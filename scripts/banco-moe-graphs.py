"""Banco CUDA graphs x MoE per la PR #27721.

Tesi da verificare: su Pascal sm_61 il guadagno dei CUDA graphs segue il numero
di nodi del grafo (decode launch-bound). Punti gia' noti: Ling-3.0-tiny
(1794 nodi, +40%) e un denso 9B (~700 nodi, +7%). Qui si aggiungono MoE di
case e architetture diverse.

Metodo, identico alla PR cosi' i numeri sono confrontabili:
  - stessa build patchata (llama-cuda124-new, gate a DP4A);
  - graphs ON = ambiente pulito, OFF = GGML_CUDA_DISABLE_GRAPHS=1;
  - sequenza A-B-A-B per modello (ON,OFF,ON,OFF) contro la deriva termica;
  - llama-bench -r 3, output json, si riporta media delle due passate;
  - conteggio nodi del grafo per modello via GGML_SCHED_DEBUG=2 (best effort).

ATTENZIONE: macchina scarica. Con 4 download in corso il tg64 di Ling scende
da ~73 a ~47 (misurato): qualsiasi processo pesante invalida il banco.
Lo script rifiuta di partire se llama-server o llama-swap sono accesi.

Una riga di avanzamento per invocazione; JSON scritto su disco man mano;
--riprendi <file> continua una corsa interrotta.
"""
import argparse, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path

BENCH = Path("d:/assistenteeee/llama-cuda124-new/llama-bench.exe")
CLI = Path("d:/assistenteeee/llama-cuda124-new/llama-cli.exe")
MODELLI_DIR = Path("d:/assistenteeee/models")
USCITA = Path("d:/vergilius-lab/ricerche/opt-1080")

MODELLI = [
    ("ling-3.0-tiny Q6_K (ancora)",      "Ling-3.0-tiny-Q6_K.gguf"),
    ("qwenpaw 9B Q5_K_M (denso, controllo)", "QwenPaw-Flash-9B.i1-Q5_K_M.gguf"),
    ("olmoe-1b-7b Q4_K_M",               "OLMoE-1B-7B-0125-Instruct-Q4_K_M.gguf"),
    ("granite-3.1-3b-a800m Q4_K_M",      "granite-3.1-3b-a800m-instruct-Q4_K_M.gguf"),
    ("granite-4.0-h-tiny Q4_K_M (mamba)", "granite-4.0-h-tiny-Q4_K_M.gguf"),
    ("lfm2.5-8b-a1b Q4_K_M",             "LFM2.5-8B-A1B-Q4_K_M.gguf"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--riprendi", type=str, default=None)
ap.add_argument("--ripetizioni", type=int, default=3)
ap.add_argument("--profondita", action="store_true",
                help="aggiunge anche tg64 a profondita' 4096 (piu' lento)")
args = ap.parse_args()


def _processi_pesanti():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process llama-server,llama-swap -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(out or "0")
    except Exception:
        return 0


if _processi_pesanti() > 0:
    print("RIFIUTO: llama-server o llama-swap accesi. Il banco richiede la "
          "macchina scarica (misurato: -36% coi download attivi). "
          "Spegni con: curl http://127.0.0.1:8012/unload e ferma llama-swap.")
    sys.exit(1)


def bench(model_path, graphs_on, rip):
    env = dict(os.environ)
    env.pop("GGML_CUDA_DISABLE_GRAPHS", None)
    if not graphs_on:
        env["GGML_CUDA_DISABLE_GRAPHS"] = "1"
    cmd = [str(BENCH), "-m", str(model_path), "-p", "512", "-n", "64,128",
           "-r", str(rip), "-o", "json"]
    if args.profondita:
        cmd += ["-d", "0,4096"]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=3600)
    try:
        dati = json.loads(p.stdout)
    except Exception:
        return None
    out = {}
    for r in dati:
        nome = ""
        if r.get("n_prompt"):
            nome = f"pp{r['n_prompt']}"
        if r.get("n_gen"):
            nome = f"tg{r['n_gen']}"
        if r.get("n_depth"):
            nome += f"@d{r['n_depth']}"
        out[nome] = (round(r.get("avg_ts", 0), 2), round(r.get("stddev_ts", 0), 2))
    return out


def conta_nodi(model_path):
    """Nodi del grafo di decode (n_tokens=1), via GGML_SCHED_DEBUG=2. Best effort."""
    env = dict(os.environ)
    env["GGML_SCHED_DEBUG"] = "2"
    try:
        p = subprocess.run(
            [str(CLI), "-m", str(model_path), "-n", "2", "-p", "ciao",
             "--no-warmup", "-no-cnv"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=600)
        testo = p.stderr + p.stdout
        # il dump elenca i grafi; l'ultimo con n_tokens=1 e' il decode.
        # le righe nodo sono " node #123" oppure "node # 12"
        blocchi = re.split(r"## SPLIT|graph splits", testo)
        migliori = 0
        for b in blocchi:
            n = len(re.findall(r"node #\s*\d+", b))
            migliori = max(migliori, n)
        totale = len(re.findall(r"node #\s*\d+", testo))
        return {"max_per_dump": migliori, "totale_righe_nodo": totale}
    except Exception:
        return None


USCITA.mkdir(parents=True, exist_ok=True)
if args.riprendi:
    fout = Path(args.riprendi)
    dati = json.loads(fout.read_text(encoding="utf-8"))
else:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fout = USCITA / f"30-banco-moe-graphs-{stamp}.json"
    dati = {"build": "b10549 b2e5e9b patchata DP4A", "ripetizioni": args.ripetizioni,
            "sequenza": "ON,OFF,ON,OFF", "risultati": {}}

SEQ = [("ON", True), ("OFF", False), ("ON", True), ("OFF", False)]

for etichetta, nomefile in MODELLI:
    mp = MODELLI_DIR / nomefile
    if not mp.exists():
        print(f"SALTO {etichetta}: manca {nomefile}", flush=True)
        continue
    r = dati["risultati"].setdefault(etichetta, {"passate": [], "nodi": None})
    if r.get("nodi") is None:
        print(f"[{etichetta}] conto i nodi del grafo...", flush=True)
        r["nodi"] = conta_nodi(mp)
        print(f"[{etichetta}] nodi: {r['nodi']}", flush=True)
        fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    for i, (nome, acceso) in enumerate(SEQ):
        if i < len(r["passate"]):
            continue  # gia' fatta (ripresa)
        t0 = time.time()
        esito = bench(mp, acceso, args.ripetizioni)
        dt = time.time() - t0
        r["passate"].append({"graphs": nome, "esito": esito, "secondi": round(dt, 1)})
        fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        riga = "  ".join(f"{k} {v[0]}±{v[1]}" for k, v in (esito or {}).items()) if esito else "ERRORE"
        print(f"[{etichetta}] {i+1}/4 graphs {nome:3}  {riga}  ({dt:.0f}s)", flush=True)

# --- tabella finale ---
print("\n=== RIEPILOGO (media delle due passate per stato) ===", flush=True)
print(f"{'modello':40} {'nodi':>6} {'tg64 OFF':>10} {'tg64 ON':>10} {'guadagno':>9}", flush=True)
for etichetta, _ in MODELLI:
    r = dati["risultati"].get(etichetta)
    if not r or len(r["passate"]) < 4:
        continue
    def media(stato, chiave="tg64"):
        vals = [p["esito"][chiave][0] for p in r["passate"]
                if p["graphs"] == stato and p.get("esito") and chiave in p["esito"]]
        return sum(vals) / len(vals) if vals else 0
    off, on = media("OFF"), media("ON")
    g = (on / off - 1) * 100 if off else 0
    nodi = (r.get("nodi") or {}).get("max_per_dump", "?")
    print(f"{etichetta:40} {nodi:>6} {off:>10.1f} {on:>10.1f} {g:>+8.1f}%", flush=True)

print(f"\nrisultati in {fout}", flush=True)
