"""Controllo d'ordine per il banco CUDA graphs (PR #27721).

La fase 1 alterna sempre ON,OFF,ON,OFF: se la posizione nella sequenza
contasse (deriva termica, costo di cattura del grafo, cache), i numeri ON
sarebbero gonfiati in modo sistematico. Qui si rompe l'alternanza sui due
modelli piu' delicati:

  granite-4.0-h-tiny  A-A-B-A  (ON,ON,OFF,ON)
  lfm2.5-8b-a1b       B-B-A-B  (OFF,OFF,ON,OFF)

Atteso, se non c'e' effetto d'ordine: gli stati ripetuti replicano se stessi
ovunque stiano nella sequenza, e le medie coincidono con la fase 1.
"""
import json, os, subprocess, time
from datetime import datetime
from pathlib import Path

BENCH = Path("d:/assistenteeee/llama-cuda124-new/llama-bench.exe")
MODELLI_DIR = Path("d:/assistenteeee/models")
USCITA = Path("d:/vergilius-lab/ricerche/opt-1080")

PIANO = [
    ("granite-4.0-h-tiny Q4_K_M (mamba)", "granite-4.0-h-tiny-Q4_K_M.gguf",
     [("ON", True), ("ON", True), ("OFF", False), ("ON", True)]),
    ("lfm2.5-8b-a1b Q4_K_M", "LFM2.5-8B-A1B-Q4_K_M.gguf",
     [("OFF", False), ("OFF", False), ("ON", True), ("OFF", False)]),
]


def bench(mp, graphs_on):
    env = dict(os.environ)
    env.pop("GGML_CUDA_DISABLE_GRAPHS", None)
    if not graphs_on:
        env["GGML_CUDA_DISABLE_GRAPHS"] = "1"
    p = subprocess.run(
        [str(BENCH), "-m", str(mp), "-p", "0", "-n", "64,128", "-r", "3", "-o", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, timeout=3600, env=env)
    try:
        d = json.loads(p.stdout)
        return {f"tg{r['n_gen']}": (round(r["avg_ts"], 2), round(r["stddev_ts"], 2))
                for r in d if r.get("n_gen")}
    except Exception:
        return None


stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
fout = USCITA / f"32-controllo-ordine-{stamp}.json"
dati = {"scopo": "rompere l'alternanza ON/OFF per escludere effetti d'ordine",
        "risultati": {}}

for etichetta, nomefile, seq in PIANO:
    mp = MODELLI_DIR / nomefile
    r = dati["risultati"].setdefault(etichetta, {"sequenza": [s for s, _ in seq], "passate": []})
    for i, (nome, acceso) in enumerate(seq):
        t0 = time.time()
        e = bench(mp, acceso)
        r["passate"].append({"graphs": nome, "esito": e})
        fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        riga = "  ".join(f"{k} {v[0]}±{v[1]}" for k, v in (e or {}).items()) if e else "ERRORE"
        print(f"[{etichetta}] ordine {i+1}/4 graphs {nome:3}  {riga}  ({time.time()-t0:.0f}s)",
              flush=True)

print("\n=== VERDETTO ORDINE ===", flush=True)
for etichetta, _, seq in PIANO:
    r = dati["risultati"][etichetta]
    for stato in ("ON", "OFF"):
        vals = [p["esito"]["tg64"][0] for p in r["passate"]
                if p["graphs"] == stato and p.get("esito")]
        if vals:
            sp = max(vals) - min(vals)
            print(f"{etichetta:38} {stato:3} {vals}  scarto max {sp:.1f}", flush=True)
print(f"\nrisultati in {fout}", flush=True)
