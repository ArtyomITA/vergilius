"""La catena WebSocket del microfono regge davvero?

Finge il browser: manda pezzi da 100 ms di PCM a 16 bit come farebbe
l'AudioWorklet, e misura quando arriva il primo testo e quando scatta la fine
turno. Poi ripete attraverso Odysseus, per verificare che anche il tramite
non aggiunga attese.

Uso:  python prova_ws_trascrizione.py [ws://...]
"""

import asyncio
import json
import sys
import time
import wave

FILE = "d:/assistenteeee/voice-samples/campione_nuovo_16k.wav"
SECONDI = 8
SILENZIO = 2.5
PEZZO_MS = 100


def pezzi():
    with wave.open(FILE, "rb") as w:
        sr = w.getframerate()
        dati = w.readframes(w.getnframes())
    per_pezzo = int(sr * PEZZO_MS / 1000) * 2  # 2 byte per campione
    parlato = dati[: sr * SECONDI * 2]
    muto = b"\x00" * (int(sr * SILENZIO) * 2)
    tutto = parlato + muto
    return [tutto[i:i + per_pezzo] for i in range(0, len(tutto), per_pezzo)]


async def prova(url, etichetta):
    import websockets

    print(f"\n=== {etichetta} ===")
    print(f"    {url}")
    blocchi = pezzi()

    try:
        ws = await websockets.connect(url, max_size=None, open_timeout=10)
    except Exception as e:
        print(f"    NON RAGGIUNGIBILE: {type(e).__name__}: {e}")
        return

    primo = None
    fine_turno = None
    parziali = 0
    ultimo_testo = ""
    t0 = time.time()

    async def ascolta():
        nonlocal primo, fine_turno, parziali, ultimo_testo
        try:
            async for grezzo in ws:
                d = json.loads(grezzo)
                if d.get("errore"):
                    print(f"    ERRORE dal server: {d['errore']}")
                    return
                if primo is None and d.get("testo"):
                    primo = time.time() - t0
                if d.get("testo"):
                    ultimo_testo = d["testo"]
                parziali += 1
                if d.get("fine_turno"):
                    fine_turno = time.time() - t0
                    return
        except Exception:
            pass

    compito = asyncio.create_task(ascolta())

    # Orario fisso, non "dormi 100 ms fra un pezzo e l'altro": il microfono
    # consegna ogni 100 ms a prescindere da quanto ci mette il riconoscitore.
    # Dormire dopo l'invio sommerebbe il tempo di decodifica e falserebbe la
    # misura facendoci arrivare sempre piu' in ritardo.
    for n, b in enumerate(blocchi):
        if compito.done():
            break
        atteso = t0 + (n * PEZZO_MS / 1000)
        ritardo = atteso - time.time()
        if ritardo > 0:
            await asyncio.sleep(ritardo)
        await ws.send(b)

    try:
        await asyncio.wait_for(compito, timeout=5)
    except asyncio.TimeoutError:
        compito.cancel()

    await ws.close()

    audio_parlato = SECONDI
    print(f"    primo testo        {primo:.2f}s" if primo else "    NESSUN testo")
    print(f"    aggiornamenti      {parziali}")
    if fine_turno:
        print(f"    fine turno         {fine_turno:.2f}s "
              f"({(fine_turno - audio_parlato)*1000:.0f} ms dopo l'ultima parola)")
    else:
        print("    fine turno         non scattata")
    print(f"    testo:             {ultimo_testo[:110]}")


async def main():
    if len(sys.argv) > 1:
        await prova(sys.argv[1], "indicato a mano")
        return
    await prova("ws://127.0.0.1:8013/v1/audio/stream?lingua=it", "ponte diretto :8013")
    await prova("ws://127.0.0.1:7000/api/stt/stream?lingua=it",
                "tramite Odysseus :7000 (serve la sessione, 403 atteso se non loggato)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
