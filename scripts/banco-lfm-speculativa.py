r"""Banco speculativa su LFM2.5-2.6B Q8_0 (GTX 1080): nessuna / DSpark / ngram.
Un server per braccio (porta 5897), greedy (temp 0, top_k 1, seed 42), 3 prompt x 2 ripetizioni x 256 token.
Misura: token/s di generazione (timings llama.cpp), token accettati dalla bozza, identita' dell'output col braccio base.
Progresso riga per riga in D:\vergilius-lab\ricerche\opt-1080\misure\lfm-speculativa.txt, dati in .json (ripresa per braccio).
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SRV = r"d:\assistenteeee\llama-pre5-b02\llama-server.exe"
M = r"C:\vergilius-build\models"
TGT = M + r"\LFM2.5-2.6B-Q8_0.gguf"
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure")
FT, FJ = OUT / "lfm-speculativa.txt", OUT / "lfm-speculativa.json"
COMUNE = ["-ngl", "999", "-fa", "on", "--ctx-size", "16384", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
          "--parallel", "1", "--host", "127.0.0.1", "--port", "5897", "--jinja"]

BRACCI = [
    ("base", []),
    ("dspark-q8-n10", ["-md", M + r"\LFM2.5-2.6B-DSpark-Q8_0.gguf", "--spec-type", "draft-dspark",
                       "--spec-draft-n-max", "10", "--spec-draft-n-min", "0", "-ngld", "999"]),
    ("dspark-f16-n10", ["-md", M + r"\LFM2.5-2.6B-DSpark-F16.gguf", "--spec-type", "draft-dspark",
                        "--spec-draft-n-max", "10", "--spec-draft-n-min", "0", "-ngld", "999"]),
    ("dspark-q8-n5", ["-md", M + r"\LFM2.5-2.6B-DSpark-Q8_0.gguf", "--spec-type", "draft-dspark",
                      "--spec-draft-n-max", "5", "--spec-draft-n-min", "0", "-ngld", "999"]),
    ("ngram-map-k", ["--spec-type", "ngram-map-k"]),
    ("dspark-q8-n3", ["-md", M + r"\LFM2.5-2.6B-DSpark-Q8_0.gguf", "--spec-type", "draft-dspark",
                      "--spec-draft-n-max", "3", "--spec-draft-n-min", "0", "-ngld", "999"]),
    ("dspark-q8-n7", ["-md", M + r"\LFM2.5-2.6B-DSpark-Q8_0.gguf", "--spec-type", "draft-dspark",
                      "--spec-draft-n-max", "7", "--spec-draft-n-min", "0", "-ngld", "999"]),
]

PROMPT = [
    ("prosa", "Spiega in italiano, in circa 200 parole, come funziona lo spread BTP-Bund e perché conta per un risparmiatore."),
    ("copia", "Riscrivi esattamente questo elenco, poi aggiungi una riga di commento per ogni voce:\n"
              "- PLTR 184.50 +3.94%\n- GD 380.03 -0.52%\n- LMT 562.09 -0.62%\n- NOC 546.47 -0.63%\n- RTX 210.54 -0.68%\n- BA 210.21 -0.89%"),
    ("json", "Produci un JSON con 8 oggetti {\"simbolo\":..., \"nome\":..., \"settore\":..., \"nota\":...} per 8 aziende della difesa USA ed europee. Solo JSON."),
]


def nota(msg):
    riga = f"{time.strftime('%H:%M:%S')} {msg}"
    print(riga, flush=True)
    with open(FT, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def gpu():
    r = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm,memory.used", "--format=csv,noheader"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def chiedi(testo):
    corpo = json.dumps({"messages": [{"role": "user", "content": testo}], "max_tokens": 256, "temperature": 0,
                        "top_k": 1, "seed": 42, "reasoning_budget_tokens": 0}).encode()
    req = urllib.request.Request("http://127.0.0.1:5897/v1/chat/completions", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def main():
    dati = json.loads(FJ.read_text(encoding="utf-8")) if FJ.exists() else {}
    for nome, extra in BRACCI:
        if nome in dati and dati[nome].get("completo"):
            nota(f"{nome}: gia' fatto, salto"); continue
        log = open(OUT / f"lfm-spec-{nome}.server.log", "wb")
        p = subprocess.Popen([SRV, "-m", TGT, *COMUNE, *extra], stdout=log, stderr=subprocess.STDOUT)
        ok = False
        for _ in range(90):
            try:
                with urllib.request.urlopen("http://127.0.0.1:5897/health", timeout=2) as r:
                    if b"ok" in r.read():
                        ok = True; break
            except Exception:
                pass
            if p.poll() is not None:
                break
            time.sleep(2)
        if not ok:
            nota(f"{nome}: SERVER NON PARTITO (vedi lfm-spec-{nome}.server.log)")
            p.kill(); dati[nome] = {"completo": True, "errore": "server non partito"}
            FJ.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8"); continue
        nota(f"{nome}: server su, gpu[{gpu()}]")
        chiedi("ciao")  # riscaldamento
        righe = []
        for tipo, testo in PROMPT:
            for rip in (1, 2):
                d = chiedi(testo)
                t = d.get("timings") or {}
                m = d["choices"][0]["message"]
                righe.append({"tipo": tipo, "rip": rip, "tg": t.get("predicted_per_second"), "n": t.get("predicted_n"),
                              "draft_n": t.get("draft_n"), "draft_acc": t.get("draft_n_accepted"),
                              "testo": (m.get("content") or "") + (m.get("reasoning_content") or "")})
                acc = (f" bozza {t.get('draft_n_accepted')}/{t.get('draft_n')}" if t.get("draft_n") else "")
                nota(f"{nome} {tipo} rip{rip}: {t.get('predicted_per_second', 0):.1f} tok/s n={t.get('predicted_n')}{acc}")
        dati[nome] = {"completo": True, "righe": righe, "gpu": gpu()}
        FJ.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        p.kill(); time.sleep(4)

    nota("RIEPILOGO (mediana tok/s per tipo; identico = stesso testo del braccio base)")
    base = {(r["tipo"], r["rip"]): r for r in (dati.get("base") or {}).get("righe", [])}
    for nome, _ in BRACCI:
        rr = (dati.get(nome) or {}).get("righe")
        if not rr:
            nota(f"  {nome}: nessun dato"); continue
        parti = []
        for tipo, _t in PROMPT:
            v = sorted(r["tg"] for r in rr if r["tipo"] == tipo and r["tg"])
            b = sorted(r["tg"] for r in base.values() if r["tipo"] == tipo and r["tg"]) if base else []
            med = v[len(v) // 2] if v else 0
            rel = f" ({med / b[len(b) // 2]:.2f}x)" if b and nome != "base" else ""
            parti.append(f"{tipo} {med:.1f}{rel}")
        ident = sum(1 for r in rr if base.get((r["tipo"], r["rip"]), {}).get("testo") == r["testo"])
        nota(f"  {nome:16} " + " | ".join(parti) + f" | identici {ident}/{len(rr)}")
    nota("BANCO FINITO")


if __name__ == "__main__":
    main()
