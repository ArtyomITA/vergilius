"""Il tramite WebSocket di Odysseus inoltra davvero?

Sulla porta 7000 la rotta e' protetta dalla sessione, ed e' giusto cosi': per
provarla servirebbe un token, e coniare un token di accesso per fare una prova
non e' una cosa da fare di nascosto.

Quindi si monta **lo stesso router** in un'applicazione nuda, senza
autenticazione, su una porta usa e getta. Quello che si verifica e' il codice
del tramite — l'unica parte scritta qui — non l'autenticazione, che e' di
Odysseus e funziona gia' (risponde 401, come deve).

Uso:  python prova_relay_stt.py
"""

import asyncio
import json
import subprocess
import sys
import time
import wave

PORTA = 7099
FILE = "d:/assistenteeee/voice-samples/campione_nuovo_16k.wav"
SECONDI = 6
SILENZIO = 2.0
PEZZO_MS = 100

APP = '''
import sys
sys.path.insert(0, "d:/assistenteeee/odysseus")
from fastapi import FastAPI
from routes.stt_routes import setup_stt_routes

class FintoServizio:
    available = False
    def get_stats(self): return {}
    def transcribe(self, b): return None

app = FastAPI()
app.include_router(setup_stt_routes(FintoServizio()))
'''


def blocchi():
    with wave.open(FILE, "rb") as w:
        sr = w.getframerate()
        dati = w.readframes(w.getnframes())
    per_pezzo = int(sr * PEZZO_MS / 1000) * 2
    tutto = dati[: sr * SECONDI * 2] + b"\x00" * (int(sr * SILENZIO) * 2)
    return [tutto[i:i + per_pezzo] for i in range(0, len(tutto), per_pezzo)]


async def prova():
    import websockets

    url = f"ws://127.0.0.1:{PORTA}/api/stt/stream?lingua=it"
    print(f"    {url}")
    ws = await websockets.connect(url, max_size=None, open_timeout=10)

    primo = None
    fine = None
    ultimo = ""
    n_msg = 0
    t0 = time.time()

    async def ascolta():
        nonlocal primo, fine, ultimo, n_msg
        try:
            async for grezzo in ws:
                d = json.loads(grezzo)
                n_msg += 1
                if d.get("errore"):
                    print(f"    ERRORE dal tramite: {d['errore']}")
                    return
                if d.get("testo"):
                    if primo is None:
                        primo = time.time() - t0
                    ultimo = d["testo"]
                if d.get("fine_turno"):
                    fine = time.time() - t0
                    return
        except Exception:
            pass

    compito = asyncio.create_task(ascolta())
    for n, b in enumerate(blocchi()):
        if compito.done():
            break
        ritardo = t0 + n * PEZZO_MS / 1000 - time.time()
        if ritardo > 0:
            await asyncio.sleep(ritardo)
        await ws.send(b)

    try:
        await asyncio.wait_for(compito, timeout=6)
    except asyncio.TimeoutError:
        compito.cancel()
    await ws.close()

    print(f"    messaggi inoltrati {n_msg}")
    print(f"    primo testo        {primo:.2f}s" if primo else "    NESSUN testo")
    if fine:
        print(f"    fine turno         {fine:.2f}s "
              f"({(fine-SECONDI)*1000:.0f} ms dopo l'ultima parola)")
    print(f"    testo:             {ultimo[:100]}")
    return primo is not None


def main():
    modulo = "d:/assistenteeee/scripts/_app_relay_prova.py"
    with open(modulo, "w", encoding="utf-8") as f:
        f.write(APP)

    proc = subprocess.Popen(
        ["d:/assistenteeee/odysseus/venv/Scripts/python.exe", "-m", "uvicorn",
         "_app_relay_prova:app", "--host", "127.0.0.1", "--port", str(PORTA)],
        cwd="d:/assistenteeee/scripts",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        time.sleep(6)
        if proc.poll() is not None:
            print("    l'applicazione di prova non e' partita:")
            print(proc.stdout.read()[-1500:])
            return 1
        ok = asyncio.run(prova())
        return 0 if ok else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== tramite di Odysseus, senza autenticazione, su porta usa e getta ===")
    sys.exit(main())
