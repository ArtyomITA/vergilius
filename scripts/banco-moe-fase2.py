"""Fase 2 del banco CUDA graphs x MoE (PR #27721).

Tre blocchi, dopo la fase 1 (pp512/tg64/tg128 A-B-A-B):
  1. nodi del grafo per modello — dalla riga "graph nodes" che llama-cli
     stampa alla creazione del contesto (niente GGML_SCHED_DEBUG: il primo
     tentativo in fase 1 moriva in timeout, llama-cli restava in conversazione
     ad aspettare stdin; qui stdin e' chiuso e il flag -no-cnv c'e' comunque);
  2. tg64 a profondita' 4096 (ON,OFF,ON,OFF) — il punto "il guadagno cala
     col KV pieno" della PR;
  3. perplexity ON contro OFF sul corpus del lavoro KL (8 chunk) — i graphs
     registrano i lanci, non cambiano la matematica: atteso identico al bit.
     Qualsiasi scarto oltre il rumore va segnalato nel thread.

Alla fine stampa la tabella markdown pronta per la PR, unendo il JSON
della fase 1. Una riga di avanzamento per invocazione, JSON scritto man mano,
--riprendi <file> continua.
"""
import argparse, glob, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path

CART = Path("d:/assistenteeee/llama-cuda124-new")
BENCH = CART / "llama-bench.exe"
CLI = CART / "llama-cli.exe"
PPL = CART / "llama-perplexity.exe"
MODELLI_DIR = Path("d:/assistenteeee/models")
USCITA = Path("d:/vergilius-lab/ricerche/opt-1080")
CORPUS = USCITA / "corpus-kld.txt"

MODELLI = [
    ("ling-3.0-tiny Q6_K (ancora)",      "Ling-3.0-tiny-Q6_K.gguf",                 "bailingmoe3", "7.9B/1.3B"),
    ("qwenpaw 9B Q5_K_M (denso, controllo)", "QwenPaw-Flash-9B.i1-Q5_K_M.gguf",     "qwen dense",  "9B/9B"),
    ("olmoe-1b-7b Q4_K_M",               "OLMoE-1B-7B-0125-Instruct-Q4_K_M.gguf",   "olmoe",       "6.9B/1.3B"),
    ("granite-3.1-3b-a800m Q4_K_M",      "granite-3.1-3b-a800m-instruct-Q4_K_M.gguf", "granitemoe", "3.3B/0.8B"),
    ("granite-4.0-h-tiny Q4_K_M (mamba)", "granite-4.0-h-tiny-Q4_K_M.gguf",         "granitehybrid", "6.9B/1B"),
    ("lfm2.5-8b-a1b Q4_K_M",             "LFM2.5-8B-A1B-Q4_K_M.gguf",               "lfm2moe",     "8.5B/1.5B"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--riprendi", type=str, default=None)
ap.add_argument("--fase1", type=str, default=None, help="JSON della fase 1 (default: il piu' recente)")
args = ap.parse_args()


def _env(graphs_on):
    env = dict(os.environ)
    env.pop("GGML_CUDA_DISABLE_GRAPHS", None)
    if not graphs_on:
        env["GGML_CUDA_DISABLE_GRAPHS"] = "1"
    return env


def conta_nodi(mp):
    """Legge la riga "graph nodes = N" che llama_context stampa al caricamento.

    llama-cli puo' restare appeso dopo la generazione (gia' successo due volte,
    TimeoutExpired anche con stdin chiuso): qui si legge lo stream riga per
    riga e si uccide il processo appena la riga compare, senza aspettare
    che esca da solo.
    """
    try:
        p = subprocess.Popen(
            [str(CLI), "-m", str(mp), "-n", "1", "-p", "ciao", "-no-cnv", "--no-warmup"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
            env=_env(True))
        trovato = None
        scadenza = time.time() + 180
        for riga in p.stdout:
            m = re.search(r"graph nodes\s*=\s*(\d+)", riga)
            if m:
                trovato = int(m.group(1))
                break
            if time.time() > scadenza:
                break
        p.kill()
        return trovato
    except Exception as e:
        print(f"    (conteggio nodi fallito: {type(e).__name__})", flush=True)
        return None


def bench_prof(mp, graphs_on):
    p = subprocess.run(
        [str(BENCH), "-m", str(mp), "-p", "0", "-n", "64", "-d", "4096",
         "-r", "3", "-o", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, timeout=3600, env=_env(graphs_on))
    try:
        d = json.loads(p.stdout)
        r = d[0]
        return (round(r["avg_ts"], 2), round(r["stddev_ts"], 2))
    except Exception:
        return None


def perplexity(mp, graphs_on):
    p = subprocess.run(
        [str(PPL), "-m", str(mp), "-f", str(CORPUS), "--chunks", "8", "-ngl", "999"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, timeout=1800, env=_env(graphs_on))
    testo = p.stderr + p.stdout
    m = re.search(r"Final estimate: PPL = ([0-9.]+) \+/- ([0-9.]+)", testo)
    return (float(m.group(1)), float(m.group(2))) if m else None


USCITA.mkdir(parents=True, exist_ok=True)
if args.riprendi:
    fout = Path(args.riprendi)
    dati = json.loads(fout.read_text(encoding="utf-8"))
else:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fout = USCITA / f"31-banco-moe-fase2-{stamp}.json"
    dati = {"risultati": {}}


def salva():
    fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")


for etichetta, nomefile, arch, taglia in MODELLI:
    mp = MODELLI_DIR / nomefile
    if not mp.exists():
        print(f"SALTO {etichetta}: manca {nomefile}", flush=True)
        continue
    r = dati["risultati"].setdefault(etichetta, {})
    if "nodi" not in r:
        r["nodi"] = conta_nodi(mp)
        print(f"[{etichetta}] nodi grafo: {r['nodi']}", flush=True)
        salva()
    prof = r.setdefault("profondita", [])
    for i, (nome, acceso) in enumerate([("ON", True), ("OFF", False), ("ON", True), ("OFF", False)]):
        if i < len(prof):
            continue
        t0 = time.time()
        e = bench_prof(mp, acceso)
        prof.append({"graphs": nome, "tg64_d4096": e})
        salva()
        print(f"[{etichetta}] prof {i+1}/4 graphs {nome:3}  tg64@d4096 "
              f"{e[0] if e else 'ERRORE'}±{e[1] if e else ''}  ({time.time()-t0:.0f}s)", flush=True)
    for stato, acceso in [("ppl_on", True), ("ppl_off", False)]:
        if stato in r:
            continue
        t0 = time.time()
        r[stato] = perplexity(mp, acceso)
        salva()
        print(f"[{etichetta}] {stato}: {r[stato]}  ({time.time()-t0:.0f}s)", flush=True)

# ---- tabella finale per la PR (markdown, inglese) ----
f1 = args.fase1
if not f1:
    cand = sorted(glob.glob(str(USCITA / "30-banco-moe-graphs-*.json")))
    f1 = cand[-1] if cand else None
fase1 = json.loads(Path(f1).read_text(encoding="utf-8"))["risultati"] if f1 else {}


def medie_fase1(etichetta, chiave):
    r = fase1.get(etichetta)
    if not r:
        return (0, 0)
    def m(stato):
        v = [p["esito"][chiave][0] for p in r["passate"]
             if p["graphs"] == stato and p.get("esito") and chiave in p["esito"]]
        return sum(v) / len(v) if v else 0
    return m("OFF"), m("ON")


def media_prof(r, stato):
    v = [p["tg64_d4096"][0] for p in r.get("profondita", [])
         if p["graphs"] == stato and p.get("tg64_d4096")]
    return sum(v) / len(v) if v else 0


print("\n\n=== TABELLA PER LA PR (incollabile) ===\n", flush=True)
print("| model | arch | params (tot/act) | graph nodes | tg64 off / on | gain | tg64 @d4096 off / on | gain @d4096 | pp512 off / on | ppl off / on |")
print("|---|---|---|---|---|---|---|---|---|---|")
for etichetta, nomefile, arch, taglia in MODELLI:
    r = dati["risultati"].get(etichetta, {})
    o64, n64 = medie_fase1(etichetta, "tg64")
    opp, npp = medie_fase1(etichetta, "pp512")
    od, nd = media_prof(r, "OFF"), media_prof(r, "ON")
    g64 = f"+{(n64/o64-1)*100:.1f}%" if o64 else "?"
    gd = f"+{(nd/od-1)*100:.1f}%" if od else "?"
    po, pn = r.get("ppl_off"), r.get("ppl_on")
    ppl = (f"{po[0]:.4f} / {pn[0]:.4f}" if po and pn else "?")
    nome_pr = etichetta.split(" (")[0]
    print(f"| {nome_pr} | {arch} | {taglia} | {r.get('nodi') or '?'} | "
          f"{o64:.1f} / {n64:.1f} | {g64} | {od:.1f} / {nd:.1f} | {gd} | "
          f"{opp:.0f} / {npp:.0f} | {ppl} |", flush=True)

print(f"\nrisultati fase 2 in {fout}", flush=True)
