"""O3-bis: divergenza DOPO un checkpoint esistente. Dice se il restore al checkpoint
funziona sull'ibrido (in O3-C la divergenza era prima del primo checkpoint: da zero, atteso).

Sequenza su slot 0 (server fresco, stessi flag di produzione + --verbose):
  1. P (~8000 token) freddo -> il server crea checkpoint durante/fine prefill (log).
  2. P' = P con divergenza nell'ULTIMO 10% (dopo l'ultimo checkpoint utile) + append.
     Atteso se restore funziona: prompt_n ~ coda (centinaia), log "restored context checkpoint".
  3. P'' = P con divergenza al 50% (nessun checkpoint prima, se min-step 8192) + append.
     Atteso: da zero, oppure restore a un checkpoint intermedio se esiste.
"""
import argparse, json, re, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("d:/assistenteeee")
SERVER = ROOT / "llama-cuda124-new/llama-server.exe"
MODEL = ROOT / "models/Ling-3.0-tiny-Q6_K.gguf"
USCITA = ROOT / "ricerche/opt-1080/misure/onda4"
PORTA = 5899
URL = f"http://127.0.0.1:{PORTA}"
FLAG = ["-m", str(MODEL), "--host", "127.0.0.1", "--port", str(PORTA), "--ctx-size", "49152",
        "--reasoning", "on", "--batch-size", "2048", "--ubatch-size", "1024", "--n-gpu-layers", "999",
        "-fa", "on", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--cache-ram", "0",
        "--load-mode", "mmap", "--slot-save-path", str(USCITA / "slotsave"), "--verbose"]

ap = argparse.ArgumentParser()
ap.add_argument("--min-step", type=int, default=None)
ap.add_argument("--ckpt", type=int, default=None)
args = ap.parse_args()
if args.min_step: FLAG += ["--checkpoint-min-step", str(args.min_step)]
if args.ckpt: FLAG += ["--ctx-checkpoints", str(args.ckpt)]
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
suff = f"-ms{args.min_step}" if args.min_step else ""
fout = USCITA / f"o3bis{suff}-{stamp}.json"
LOG = fout.with_suffix(".server.log")


def riga(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def post(p, corpo, timeout=900):
    req = urllib.request.Request(f"{URL}{p}", data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def log_pos():
    return LOG.stat().st_size if LOG.exists() else 0


def log_da(pos):
    with open(LOG, "rb") as f:
        f.seek(pos)
        t = f.read().decode("utf-8", errors="replace")
    return [r.strip()[:170] for r in t.splitlines() if "checkpoint" in r or "forcing full" in r][-10:]


def compl(prompt, slot):
    p0 = log_pos()
    d = post("/completion", {"prompt": prompt, "n_predict": 8, "temperature": 0,
                             "cache_prompt": True, "id_slot": slot})
    tm = d.get("timings", {})
    return {"prompt_n": tm.get("prompt_n"), "cache_n": tm.get("cache_n"),
            "prompt_ms": tm.get("prompt_ms"), "log": log_da(p0)}


def testo(n_tok, seme):
    base = ("Il {i}° rapporto {s} descrive la manutenzione della centrale idrica di {c}: portata {p} "
            "litri al secondo, pressione {q} bar, temperatura {t} gradi, intervento il giorno {g}. ")
    citta = ["Trento", "Bari", "Lecco", "Aosta", "Enna", "Pisa", "Udine", "Fermo"]
    parti, i = [], 0
    while True:
        parti.append(base.format(i=i, s=seme, c=citta[i % 8], p=100 + i * 7, q=3 + i % 9,
                                 t=10 + i % 25, g=1 + i % 28))
        i += 1
        if i % 40 == 0:
            t = "".join(parti)
            n = len(post("/tokenize", {"content": t})["tokens"])
            if n >= n_tok:
                return t, n


logf = open(LOG, "a", encoding="utf-8", errors="replace")
srv = subprocess.Popen([str(SERVER)] + FLAG, stdout=logf, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL)
try:
    for _ in range(180):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=2); break
        except Exception:
            pass
    riga("server pronto")
    P, nP = testo(8000, "O3B")
    riga(f"prefisso {nP} token")
    esiti = {"prefisso_token": nP}
    a = compl(P, 0); esiti["1_freddo"] = a
    riga(f"1 freddo: prompt_n {a['prompt_n']}")
    for l in a["log"]:
        riga("   " + l)
    # divergenza nell'ultimo 10%: cambio una citta' negli ultimi paragrafi
    taglio = int(len(P) * 0.9)
    P_coda = P[:taglio] + P[taglio:].replace("Trento", "Torino")
    b = compl(P_coda + " Domanda: portata a Bari?", 0); esiti["2_divergenza_ultimo_10pct"] = b
    riga(f"2 divergenza ultimo 10%: prompt_n {b['prompt_n']} cache_n {b['cache_n']} (atteso: centinaia se restore ok)")
    for l in b["log"]:
        riga("   " + l)
    # ripristino stato: rimando P intero (riprocesso quello che serve), poi divergenza a meta'
    compl(P, 0)
    meta = int(len(P) * 0.5)
    P_meta = P[:meta] + P[meta:].replace("Bari", "Bologna", 2) if "Bari" in P[meta:] else P[:meta] + "X" + P[meta:]
    c = compl(P_meta + " Domanda: portata a Bari?", 0); esiti["3_divergenza_50pct"] = c
    riga(f"3 divergenza al 50%: prompt_n {c['prompt_n']} cache_n {c['cache_n']}")
    for l in c["log"]:
        riga("   " + l)
    fout.write_text(json.dumps(esiti, ensure_ascii=False, indent=1), encoding="utf-8")
    riga(f"fine -> {fout}")
finally:
    if srv.poll() is None:
        srv.kill(); srv.wait(timeout=30)
    if not logf.closed:
        logf.close()
