"""Correttezza decode con CUDA graphs, per PR #27721.

La perplexity esercita il grafo batch-512 (prefill), non quello batch-1 del
decode dove vivono i guadagni. Qui la prova giusta: generazione greedy
(temperature 0, top_k 1, seed fisso), stesso prompt, graphs ON contro OFF,
confronto byte per byte. 3 prompt per modello, 128 token l'uno.

In piu': llama-server stampa "graph nodes = A (with bs=N), B (with bs=1)" al
caricamento — si raccoglie B (nodi del grafo di decode) per la colonna nodi.

Vietato girare con banchi attivi. Un server per volta, porta 5899, kill a fine giro.
"""
import json, os, re, subprocess, time, urllib.request
from datetime import datetime
from pathlib import Path

SERVER = Path("d:/assistenteeee/llama-cuda124-new/llama-server.exe")
MODELLI_DIR = Path("d:/assistenteeee/models")
USCITA = Path("d:/vergilius-lab/ricerche/opt-1080")
PORTA = 5899

MODELLI = [
    ("ling-3.0-tiny Q6_K",      "Ling-3.0-tiny-Q6_K.gguf"),
    ("qwenpaw 9B Q5_K_M denso", "QwenPaw-Flash-9B.i1-Q5_K_M.gguf"),
    ("olmoe-1b-7b",             "OLMoE-1B-7B-0125-Instruct-Q4_K_M.gguf"),
    ("granite-3.1-3b-a800m",    "granite-3.1-3b-a800m-instruct-Q4_K_M.gguf"),
    ("granite-4.0-h-tiny",      "granite-4.0-h-tiny-Q4_K_M.gguf"),
    ("lfm2.5-8b-a1b",           "LFM2.5-8B-A1B-Q4_K_M.gguf"),
]

PROMPT = [
    "Calcola passo passo: 347 * 29 + 1156 / 4 =",
    "Scrivi un paragrafo sulla storia della stampa a caratteri mobili.",
    "Write a python function that merges two sorted lists into one sorted list.",
]


def avvia(mp, graphs_on):
    env = dict(os.environ)
    env.pop("GGML_CUDA_DISABLE_GRAPHS", None)
    if not graphs_on:
        env["GGML_CUDA_DISABLE_GRAPHS"] = "1"
    p = subprocess.Popen(
        [str(SERVER), "-m", str(mp), "--port", str(PORTA), "--host", "127.0.0.1",
         "-ngl", "999", "--ctx-size", "4096"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, env=env)
    nodi = None
    scadenza = time.time() + 300
    for riga in p.stdout:
        m = re.search(r"graph nodes\s*=\s*\d+ \(with bs=\d+\), (\d+) \(with bs=1\)", riga)
        if m:
            nodi = int(m.group(1))
        if "listening on" in riga:   # b10549: SRV_INF("listening on %s")
            break
        if time.time() > scadenza:
            p.kill()
            return None, None
    # drena il log in un thread implicito: da qui in poi non leggiamo piu' stdout,
    # il buffer della pipe puo' riempirsi e bloccare il server -> DEVNULL non
    # possibile a posteriori, quindi si continua a leggere in background.
    import threading
    threading.Thread(target=lambda: [None for _ in p.stdout], daemon=True).start()
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health", timeout=2)
            return p, nodi
        except Exception:
            time.sleep(1)
    p.kill()
    return None, nodi


def genera(prompt):
    corpo = json.dumps({"prompt": prompt, "n_predict": 128, "temperature": 0,
                        "top_k": 1, "seed": 42, "cache_prompt": False}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/completion", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["content"]


stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
fout = USCITA / f"34-greedy-decode-{stamp}.json"
dati = {"metodo": "greedy temp0 topk1 seed42, 3 prompt x 128 token, ON vs OFF",
        "risultati": {}}

for etichetta, nomefile in MODELLI:
    mp = MODELLI_DIR / nomefile
    if not mp.exists():
        print(f"SALTO {etichetta}", flush=True)
        continue
    r = {"nodi_bs1": None, "testi": {}}
    ok = True
    for stato, acceso in [("ON", True), ("OFF", False)]:
        p, nodi = avvia(mp, acceso)
        if p is None:
            print(f"[{etichetta}] {stato}: SERVER NON PARTITO", flush=True)
            ok = False
            break
        if acceso and nodi:
            r["nodi_bs1"] = nodi
        testi = []
        for i, pr in enumerate(PROMPT):
            t0 = time.time()
            try:
                testi.append(genera(pr))
            except Exception as e:
                testi.append(f"ERRORE {type(e).__name__}")
            print(f"[{etichetta}] {stato} prompt {i+1}/3  {time.time()-t0:.1f}s", flush=True)
        r["testi"][stato] = testi
        p.kill()
        time.sleep(2)
    if ok and "ON" in r["testi"] and "OFF" in r["testi"]:
        uguali = sum(1 for a, b in zip(r["testi"]["ON"], r["testi"]["OFF"]) if a == b)
        r["identici"] = f"{uguali}/3"
        print(f"[{etichetta}] nodi bs=1: {r['nodi_bs1']}  identici: {uguali}/3", flush=True)
    dati["risultati"][etichetta] = r
    fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")

print("\n=== RIEPILOGO ===", flush=True)
for etichetta, _ in MODELLI:
    r = dati["risultati"].get(etichetta) or {}
    print(f"{etichetta:28} nodi(bs=1) {r.get('nodi_bs1') or '?':>5}  "
          f"greedy identici {r.get('identici','?')}", flush=True)
print(f"dati in {fout}", flush=True)
