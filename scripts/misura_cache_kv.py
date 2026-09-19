"""Quanto costa cambiare il prefisso del prompt?

La domanda dietro Headroom in modalita' proxy: se si comprime la cronologia, il
prefisso cambia a ogni turno e llama.cpp non puo' riusare la cache KV. Bisogna
sapere quanto costa quel riprocessamento **sul nostro hardware**, non in teoria.

Tre scenari, stesso numero di token:

  A  prefisso identico, coda nuova   -> la cache regge (turno normale)
  B  prefisso cambiato all'inizio    -> cache buttata (compressione a monte)
  C  prefisso cambiato a meta'       -> cache parziale (compattazione a meta')

llama.cpp riporta i tempi in `timings`: `prompt_n`, `prompt_ms`,
`cache_n` (token riusati dalla cache).
"""

import json
import sys
import time
import urllib.request

LLAMA = "http://127.0.0.1:8012/v1/chat/completions"
MODELLO = sys.argv[1] if len(sys.argv) > 1 else "qwenpaw"

# Testo di riempimento: frasi diverse fra loro, cosi' i token non si ripetono
# in modo innaturale e la misura resta onesta.
def riempimento(n_frasi, seme=0):
    return " ".join(
        f"Il rilevamento numero {seme*10000+i} riporta una anomalia di categoria "
        f"{(seme*7+i) % 23} nel settore {(i*3+seme) % 97} con indice {(i % 41)/7:.2f}."
        for i in range(n_frasi)
    )


def chiama(messaggi, max_tokens=8, timeout=600):
    corpo = {"model": MODELLO, "messages": messaggi,
             "temperature": 0.1, "max_tokens": max_tokens}
    req = urllib.request.Request(LLAMA, data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d, time.time() - t0


def tempi(d):
    t = d.get("timings") or {}
    u = d.get("usage") or {}
    return {
        "prompt_n": t.get("prompt_n") or u.get("prompt_tokens"),
        "prompt_ms": t.get("prompt_ms"),
        "cache_n": t.get("cache_n"),
        "prompt_per_sec": t.get("prompt_per_second"),
    }


def riga(etichetta, d, secondi):
    t = tempi(d)
    n = t["prompt_n"] or 0
    cache = t["cache_n"]
    ms = t["prompt_ms"]
    vel = t["prompt_per_sec"]
    riusati = f"{cache}" if cache is not None else "n/d"
    print(f"  {etichetta:<38} {n:>6} tok  riusati {riusati:>6}  "
          f"prompt {ms/1000 if ms else 0:>6.2f}s  {vel or 0:>6.0f} tok/s  totale {secondi:>5.1f}s")
    return t


def main():
    print(f"modello: {MODELLO}\n")

    SIST = "Sei un assistente. Rispondi in una parola."
    base = riempimento(700, seme=1)          # ~15-18K token di contesto
    print("=== scaldo il modello e riempio la cache ===")
    d, s = chiama([{"role": "system", "content": SIST},
                   {"role": "user", "content": base + "\n\nDomanda: va bene?"}])
    riga("primo giro (cache fredda)", d, s)

    print("\n=== A. PREFISSO IDENTICO, coda nuova (turno normale) ===")
    d, s = chiama([{"role": "system", "content": SIST},
                   {"role": "user", "content": base + "\n\nDomanda: e adesso?"}])
    a = riga("stesso prefisso", d, s)

    print("\n=== B. PREFISSO CAMBIATO ALL'INIZIO (compressione a monte) ===")
    # Una sola parola diversa all'inizio invalida tutto quello che segue.
    d, s = chiama([{"role": "system", "content": SIST + " Sii conciso."},
                   {"role": "user", "content": base + "\n\nDomanda: e adesso?"}])
    b = riga("prima riga diversa", d, s)

    print("\n=== C. PREFISSO CAMBIATO A META' (compattazione) ===")
    meta = riempimento(350, seme=1) + " " + riempimento(350, seme=9)
    d, s = chiama([{"role": "system", "content": SIST},
                   {"role": "user", "content": meta + "\n\nDomanda: e adesso?"}])
    c = riga("seconda meta' diversa", d, s)

    print("\n=== D. di nuovo A, per confermare che la cache regge ===")
    d, s = chiama([{"role": "system", "content": SIST},
                   {"role": "user", "content": base + "\n\nDomanda: e adesso?"}])
    riga("stesso prefisso, ripetuto", d, s)

    print("\n" + "=" * 78)
    if a.get("prompt_ms") and b.get("prompt_ms"):
        costo = (b["prompt_ms"] - a["prompt_ms"]) / 1000
        print(f"  Cambiare il prefisso costa {costo:+.2f}s su ~{a['prompt_n']} token di contesto")
        if a["prompt_ms"] > 0:
            print(f"  cioe' {b['prompt_ms']/max(a['prompt_ms'],1):.0f} volte il tempo di prompt di un turno normale")
    print("  (a ogni turno: una conversazione da 20 turni paga questo 20 volte)")


if __name__ == "__main__":
    main()
