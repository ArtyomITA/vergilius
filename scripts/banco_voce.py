"""Banco di prova della voce in ingresso: quanto tardi arriva il testo, e
quando il ponte decide che hai finito di parlare.

Fa quello che fa il browser, con gli stessi byte: PCM 16 bit mono a 16 kHz,
pezzi da 100 ms, mandati **a orario reale** (non "dormi 100 ms fra un pezzo e
l'altro": quello sommerebbe il tempo di decodifica e farebbe sembrare tutto piu'
lento di com'e').

Misura tre cose, che sono le tre lamentele:

  * primo parziale      — quanto ci mette a comparire la prima parola
  * fine turno          — quanti ms dopo l'ultima parola si chiude il turno
  * fine turno false    — quante volte si chiude **mentre** stai ancora parlando
                          (le pause a meta' frase: respiro, "ehm", virgola)

Le tracce di prova si costruiscono dal campione italiano vero tagliandolo e
rimettendolo insieme con silenzi in mezzo: niente dipendenze nuove, niente
registrazioni da rifare.

Uso:
    python banco_voce.py                       # ponte diretto :8013
    python banco_voce.py --url ws://127.0.0.1:7000/api/stt/stream
    python banco_voce.py --prove dritto,pausa400
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
import wave

CAMPIONE = "d:/assistenteeee/voice-samples/campione_nuovo_16k.wav"
PONTE = "ws://127.0.0.1:8013/v1/audio/stream"
PEZZO_MS = 100
CODA_SILENZIO_S = 2.5


# ── costruzione delle tracce ────────────────────────────────────────────────

def leggi(percorso):
    with wave.open(percorso, "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, "serve mono 16 bit"
        return w.readframes(w.getnframes()), w.getframerate()


def silenzio(sr, secondi):
    return b"\x00" * (int(sr * secondi) * 2)


def con_pause(parlato, sr, pausa_s, segmento_s=2.0):
    """Spezza il parlato e infila una pausa fra un pezzo e l'altro.

    E' il caso che rompe la fine turno a soglia unica: una pausa di respiro a
    meta' frase e' indistinguibile, per il solo silenzio, dalla fine del turno.
    """
    passo = int(sr * segmento_s) * 2
    pezzi = [parlato[i:i + passo] for i in range(0, len(parlato), passo)]
    return silenzio(sr, pausa_s).join(pezzi)


def tracce(nomi):
    grezzo, sr = leggi(CAMPIONE)
    parlato = grezzo[: sr * 8 * 2]          # 8 s bastano e avanzano
    catalogo = {
        # nome: (audio, secondi di parlato prima della coda di silenzio)
        "dritto": (parlato + silenzio(sr, CODA_SILENZIO_S), 8.0),
        "pausa400": (con_pause(parlato, sr, 0.4) + silenzio(sr, CODA_SILENZIO_S),
                     8.0 + 3 * 0.4),
        "pausa700": (con_pause(parlato, sr, 0.7) + silenzio(sr, CODA_SILENZIO_S),
                     8.0 + 3 * 0.7),
        "muto": (silenzio(sr, 5.0), 0.0),
    }
    return sr, [(n, *catalogo[n]) for n in nomi if n in catalogo]


# ── una corsa ───────────────────────────────────────────────────────────────

async def corsa(url, nome, audio, fine_parlato_s, sr):
    import websockets

    per_pezzo = int(sr * PEZZO_MS / 1000) * 2
    blocchi = [audio[i:i + per_pezzo] for i in range(0, len(audio), per_pezzo)]

    try:
        ws = await websockets.connect(url, max_size=None, open_timeout=10)
    except Exception as e:
        print(f"  {nome:9s} NON RAGGIUNGIBILE: {type(e).__name__}: {e}")
        return None

    eventi = []          # (istante, fine_turno, testo)
    t0 = time.time()

    async def ascolta():
        try:
            async for grezzo in ws:
                d = json.loads(grezzo)
                if d.get("errore"):
                    eventi.append((time.time() - t0, None, "ERRORE: " + d["errore"]))
                    return
                eventi.append((time.time() - t0, bool(d.get("fine_turno")),
                               d.get("testo") or ""))
        except Exception:
            pass

    compito = asyncio.create_task(ascolta())
    for n, b in enumerate(blocchi):
        ritardo = t0 + n * PEZZO_MS / 1000 - time.time()
        if ritardo > 0:
            await asyncio.sleep(ritardo)
        await ws.send(b)

    # Si aspetta ancora un po': la fine turno puo' arrivare dopo l'ultimo pezzo.
    await asyncio.sleep(1.5)
    compito.cancel()
    await ws.close()

    parziali = [e for e in eventi if e[1] is False and e[2]]
    turni = [e for e in eventi if e[1] is True]
    # "Falsa" = chiusa prima che il parlato fosse finito (meno un margine).
    false = [t for t in turni if t[0] < fine_parlato_s - 0.3]
    dopo = [t for t in turni if t[0] >= fine_parlato_s - 0.3]

    primo = parziali[0][0] if parziali else None
    testo = " ".join(t[2] for t in turni if t[2]) or (parziali[-1][2] if parziali else "")

    print(f"  {nome:9s} primo parziale {('%.2fs' % primo) if primo else '  --  '}"
          f"   aggiornamenti {len(parziali):3d}"
          f"   turni {len(turni)}  (false {len(false)})", end="")
    if dopo:
        print(f"   fine turno +{(dopo[0][0] - fine_parlato_s) * 1000:.0f} ms")
    else:
        print("   fine turno NON scattata")
    for t in false:
        print(f"            ! chiusura anticipata a {t[0]:.2f}s: {t[2][-45:]!r}")
    if testo:
        print(f"            testo: {testo[:160]}")
    return {"nome": nome, "primo": primo, "turni": len(turni),
            "false": len(false), "testo": testo}


def ram_ponte():
    """RSS del processo del ponte, in MB. Senza dipendenze: usa tasklist."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return None
    totali = []
    for riga in out.splitlines():
        campi = [c.strip('"') for c in riga.split('","')]
        if len(campi) >= 5:
            try:
                totali.append(int(campi[4].replace(".", "").replace(",", "")
                                  .replace(" K", "").strip()) / 1024)
            except ValueError:
                pass
    return max(totali) if totali else None


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=PONTE)
    ap.add_argument("--lingua", default="it")
    ap.add_argument("--prove", default="dritto,pausa400,pausa700,muto")
    args = ap.parse_args()

    url = f"{args.url}?lingua={args.lingua}"
    sr, elenco = tracce([n.strip() for n in args.prove.split(",")])

    print(f"banco voce — {url}")
    print(f"campione: {CAMPIONE} ({sr} Hz)\n")

    for nome, audio, fine in elenco:
        await corsa(url, nome, audio, fine, sr)

    ram = ram_ponte()
    if ram:
        print(f"\nRAM del python piu' grosso (il ponte): {ram:.0f} MB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
