r"""Prova dei modelli candidati sul banco System One (27 set 2026): MiniCPM5-2B, Uraion Forge 2B e LFM2.5 in inglese.

Esegue in fila, una prova alla volta, e riprende da dove era: ogni prova finita lascia una riga FATTO nel registro.
Per ogni prova: avvia llama-server (binario di produzione llama-pre5-b02, niente kernel custom), aspetta /health, lancia
scripts/banco-system-one.py --diretto, ferma il server. Nessun servizio di Vergilius coinvolto.

Uso: py scripts\prova-candidati-system-one.py            (tutte le prove mancanti)
     py scripts\prova-candidati-system-one.py --solo minicpm5-it-ragiona
Registro: D:\vergilius-lab\ricerche\minicpm5\prova-candidati.txt
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

QUI = Path(__file__).resolve().parent
SRV = r"d:\assistenteeee\llama-pre5-b02\llama-server.exe"
M = Path(r"C:\vergilius-build\models")
OUT = Path(r"D:\vergilius-lab\ricerche\minicpm5")
REGISTRO = OUT / "prova-candidati.txt"
PORTA = 8031
EN = str(QUI / "banco-system-one-domande-en.json")

COMUNE = ["--host", "127.0.0.1", "--port", str(PORTA), "--ctx-size", "49152", "--jinja", "--batch-size", "2048",
          "--ubatch-size", "1024", "--n-gpu-layers", "999", "-fa", "on", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
          "--cache-ram", "0", "--metrics", "--slot-save-path", str(OUT / "slotsave")]
MINICPM_CAMPIONI = ["--temp", "1.0", "--top-p", "0.95", "--min-p", "0.0"]
MINICPM_BOZZA = ["-md", str(M / "MiniCPM5-2.6B-DSpark-Q8_0.gguf"), "-ngld", "999", "--spec-type", "draft-dspark",
                 "--spec-draft-n-max", "5", "--spec-draft-n-min", "0"]
SERVER = {
    "minicpm5": ["-m", str(M / "MiniCPM5-2B-Q8_0.gguf"), *MINICPM_CAMPIONI, *MINICPM_BOZZA],
    "forge": ["-m", str(M / "uraion-forge-2b-q8_0.gguf"), "--chat-template-file", str(M / "MiniCPM5-2B-chat_template.jinja"),
              *MINICPM_CAMPIONI, *MINICPM_BOZZA],
    # stessi parametri della produzione (llama-swap/config.yaml, profilo lfm)
    "lfm": ["-m", str(M / "LFM2.5-2.6B-Q8_0.gguf"), "--temp", "0.1", "--top-k", "50", "--repeat-penalty", "1.1",
            "-md", str(M / "LFM2.5-2.6B-DSpark-Q8_0.gguf"), "-ngld", "999", "--spec-type", "draft-dspark",
            "--spec-draft-n-max", "3", "--spec-draft-n-min", "0"],
}
GGUF = {"minicpm5": M / "MiniCPM5-2B-Q8_0.gguf", "forge": M / "MiniCPM5-2B-Q8_0.gguf", "lfm": M / "LFM2.5-2.6B-Q8_0.gguf"}
# (nome, server, dataset o None per l'italiano, braccio)
PROVE = [
    ("minicpm5-it-ragiona", "minicpm5", None, "ragiona"),
    ("minicpm5-en", "minicpm5", EN, "entrambi"),
    ("forge-it", "forge", None, "entrambi"),
    ("forge-en", "forge", EN, "entrambi"),
    ("lfm-en", "lfm", EN, "entrambi"),
]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def fatte():
    if not REGISTRO.exists():
        return set()
    return {r.split("FATTO ", 1)[1].split()[0] for r in REGISTRO.read_text(encoding="utf-8").splitlines() if "FATTO " in r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "slotsave").mkdir(exist_ok=True)
    gia = fatte()
    for nome, srv, dataset, braccio in PROVE:
        if a.solo and nome != a.solo:
            continue
        if nome in gia:
            nota(f"{nome}: gia' fatta, salto")
            continue
        log = open(OUT / f"server-{nome}.log", "wb")
        p = subprocess.Popen([SRV, *SERVER[srv], *COMUNE], stdout=log, stderr=subprocess.STDOUT)
        pronto = False
        for _ in range(120):
            try:
                if b"ok" in urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health", timeout=2).read():
                    pronto = True
                    break
            except Exception:
                pass
            if p.poll() is not None:
                break
            time.sleep(2)
        if not pronto:
            nota(f"{nome}: SERVER NON PARTITO (vedi server-{nome}.log)")
            p.kill()
            continue
        nota(f"{nome}: server pronto ({srv}), banco braccio={braccio} dataset={'EN' if dataset else 'IT'}")
        cmd = [sys.executable, str(QUI / "banco-system-one.py"), "--gguf", str(GGUF[srv]), "--diretto",
               "--base", f"http://127.0.0.1:{PORTA}", "--modello", srv, "--braccio", braccio]
        if dataset:
            cmd += ["--dataset", dataset]
        esito = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        coda = [r for r in esito.stdout.splitlines() if r.strip()][-3:]
        p.kill()
        p.wait(timeout=30)
        time.sleep(4)
        if esito.returncode == 0:
            nota(f"FATTO {nome} | " + " / ".join(coda)[-300:])
        else:
            nota(f"{nome}: banco uscito con {esito.returncode}: " + (esito.stderr or esito.stdout)[-400:])
    nota("PROVE FINITE")


if __name__ == "__main__":
    main()
