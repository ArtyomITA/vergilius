"""Ponte OpenAI-compatibile per la voce locale.

Traduce le chiamate che Odysseus sa fare (formato OpenAI) verso i motori locali:

    POST /v1/audio/speech          -> PocketTTS  (127.0.0.1:8014/tts)
    POST /v1/audio/transcriptions  -> Parakeet   (onnx-asr, in-process)
    GET  /v1/models                -> elenco fittizio, serve solo alla sonda di Odysseus

Odysseus chiede sempre formato mp3 ma riconosce il tipo dai primi byte del file,
quindi restituire WAV va bene e ci risparmia una conversione.

Avvio:  python ponte_voce.py       (porta 8013)
"""

import io
import logging
import os
import tempfile

import httpx
from fastapi import (FastAPI, File, Form, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect)
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

import asr_streaming

POCKETTTS_URL = os.getenv("POCKETTTS_URL", "http://127.0.0.1:8014/tts")
STT_MODEL_ID = os.getenv("STT_MODEL", "nemo-parakeet-tdt-0.6b-v3")
# "estelle" e' la voce FRANCESE del catalogo Kyutai (developpeuse-3.wav) e per
# mesi e' stata la predefinita sopra il modello italiano: accento e cadenza
# sbagliati a ogni frase. Per l'italiano il pacchetto prevede "giovanni".
DEFAULT_VOICE = os.getenv("TTS_VOICE", "giovanni")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ponte-voce")

app = FastAPI(title="Ponte voce locale")

# Il modello di trascrizione si carica alla prima richiesta: l'avvio resta veloce
# e chi usa solo il TTS non paga i 2GB di RAM.
_stt_model = None


def get_stt():
    global _stt_model
    if _stt_model is None:
        import onnx_asr

        logger.info("carico il modello di trascrizione %s...", STT_MODEL_ID)
        _stt_model = onnx_asr.load_model(STT_MODEL_ID)
        logger.info("modello di trascrizione pronto")
    return _stt_model


class SpeechRequest(BaseModel):
    model: str = "pocket-tts"
    input: str
    voice: str = DEFAULT_VOICE
    response_format: str = "wav"
    speed: float = 1.0


@app.on_event("startup")
def scalda_asr():
    """Il modello in streaming si carica all'avvio, non alla prima frase.

    Sono ~5 secondi e ~700 MB. Pagarli pigramente vorrebbe dire perdere la prima
    frase della sessione, che e' esattamente quella in cui si dice "ciao" e si
    giudica se il coso funziona."""
    if not asr_streaming.disponibile():
        logger.warning("trascrizione in streaming non disponibile: modello o "
                       "sherpa-onnx mancanti, resta il giro a lotti")
        return
    import threading
    threading.Thread(target=asr_streaming.carica, daemon=True).start()


@app.on_event("startup")
def scalda_tts():
    """Prima frase della sessione: la paga il banco di prova, non l'utente.

    PocketTTS tiene l'incastro della voce in una cache di processo: alla prima
    richiesta dopo l'avvio deve leggerlo (e la prima volta in assoluto anche
    scaricarlo) e far girare il modello a freddo. Misurato: primo byte a 1,8 s
    a freddo contro 0,65 s a caldo, e fino a 7 s se l'incastro non c'e' ancora
    su disco. Sono esattamente i secondi di silenzio dopo la prima risposta.

    PocketTTS ci mette ~8-13 s ad aprire la porta, quindi si riprova in
    sottofondo finche' non risponde, senza bloccare l'avvio del ponte.
    """
    import threading

    def riscalda():
        import time
        scadenza = time.monotonic() + 180
        while time.monotonic() < scadenza:
            try:
                r = httpx.post(POCKETTTS_URL, timeout=httpx.Timeout(120.0, connect=2.0),
                               data={"text": "Pronto.", "voice_url": DEFAULT_VOICE})
                if r.status_code == 200:
                    logger.info("sintesi scaldata con la voce %s", DEFAULT_VOICE)
                    return
                logger.warning("riscaldamento sintesi: PocketTTS ha risposto %s", r.status_code)
                return
            except httpx.ConnectError:
                time.sleep(3)   # non e' ancora in piedi
            except Exception as e:  # noqa: BLE001
                logger.warning("riscaldamento sintesi fallito: %s", e)
                return
        logger.warning("riscaldamento sintesi: PocketTTS non si e' fatto vivo")

    threading.Thread(target=riscalda, daemon=True).start()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "stt_loaded": _stt_model is not None,
        "stream_disponibile": asr_streaming.disponibile(),
        "stream_caricato": asr_streaming._riconoscitore is not None,
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "pocket-tts", "object": "model", "owned_by": "locale"},
            {"id": "parakeet", "object": "model", "owned_by": "locale"},
        ],
    }


@app.post("/v1/audio/speech")
async def speech(req: SpeechRequest):
    """Passa l'audio mentre arriva, non quando e' finito.

    PocketTTS risponde gia' con `StreamingResponse` e un'intestazione WAV con un
    numero di campioni fittizio (un miliardo), fatta apposta per essere letta
    prima che il file esista per intero. La versione precedente faceva
    `await client.post(...)` e poi restituiva `resp.content`: aspettava tutto il
    file, e i ~200 ms di primo pezzo diventavano i 2-3 secondi della frase
    intera. Qui il flusso passa senza mai essere raccolto in memoria.
    """
    text = (req.input or "").strip()
    if not text:
        raise HTTPException(400, "input vuoto")

    client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))
    richiesta = client.build_request(
        "POST", POCKETTTS_URL,
        data={"text": text, "voice_url": req.voice or DEFAULT_VOICE},
    )

    try:
        risposta = await client.send(richiesta, stream=True)
    except httpx.ConnectError:
        await client.aclose()
        raise HTTPException(503, f"PocketTTS non raggiungibile su {POCKETTTS_URL}")
    except Exception:
        await client.aclose()
        raise

    if risposta.status_code != 200:
        corpo = (await risposta.aread())[:200]
        await risposta.aclose()
        await client.aclose()
        raise HTTPException(502, f"PocketTTS ha risposto {risposta.status_code}: {corpo!r}")

    async def flusso():
        # Il client va chiuso qui dentro, non fuori: se lo si chiude prima che il
        # generatore finisca, la connessione muore a meta' frase.
        try:
            async for pezzo in risposta.aiter_bytes():
                yield pezzo
        finally:
            await risposta.aclose()
            await client.aclose()

    return StreamingResponse(
        flusso(),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form("parakeet"),
    language: str = Form("it"),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "file audio vuoto")

    # onnx-asr legge da percorso; il browser manda webm/ogg, che va convertito.
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        src_path = tmp.name

    wav_path = src_path + ".wav"
    try:
        _to_wav(src_path, wav_path)
        text = get_stt().recognize(wav_path, language=language or None)
        return JSONResponse({"text": (text or "").strip()})
    except FileNotFoundError as e:
        raise HTTPException(500, f"conversione audio fallita: {e}")
    finally:
        for p in (src_path, wav_path):
            try:
                os.unlink(p)
            except OSError:
                pass


@app.websocket("/v1/audio/stream")
async def trascrizione_in_diretta(ws: WebSocket):
    """Microfono acceso: PCM in ingresso, testo in uscita, senza attese.

    Protocollo, volutamente minimo:

      client -> server   messaggi binari: PCM 16 bit little endian, mono, 16 kHz
                         messaggio di testo "fine"   -> chiudi e restituisci tutto
      server -> client   {"testo": "...", "fine_turno": false}   mentre parli
                         {"testo": "...", "fine_turno": true}    quando taci

    `fine_turno` e' quello che sostituisce il pulsante di stop: lo decide il
    riconoscitore in base al silenzio, non l'utente con un click.
    """
    await ws.accept()

    if not asr_streaming.disponibile():
        await ws.send_json({"errore": "modello di trascrizione non installato"})
        await ws.close()
        return

    lingua = ws.query_params.get("lingua") or asr_streaming.LINGUA_PREDEFINITA
    try:
        sessione = asr_streaming.Sessione(lingua)
    except Exception as e:
        logger.exception("apertura sessione fallita")
        await ws.send_json({"errore": f"{type(e).__name__}: {e}"})
        await ws.close()
        return

    try:
        while True:
            msg = await ws.receive()

            if msg.get("type") == "websocket.disconnect":
                break

            testo_ricevuto = msg.get("text")
            if testo_ricevuto is not None:
                if testo_ricevuto.strip().lower() == "fine":
                    await ws.send_json({"testo": sessione.finito(),
                                        "fine_turno": True, "chiuso": True})
                    break
                continue

            dati = msg.get("bytes")
            if not dati:
                continue

            campioni = asr_streaming.da_pcm16(dati)
            testo, cambiato, fine = sessione.aggiungi(campioni)

            if fine:
                # Il turno si chiude qui: si manda il testo definitivo e si
                # riparte, cosi' chi ascolta puo' gia' inoltrarlo al modello.
                await ws.send_json({"testo": sessione.chiudi_turno(),
                                    "fine_turno": True})
            elif cambiato:
                await ws.send_json({"testo": testo, "fine_turno": False})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("errore durante la trascrizione in diretta")
    finally:
        try:
            await ws.close()
        except Exception:
            pass


def _to_wav(src: str, dst: str) -> None:
    """16 kHz mono, il formato che il modello si aspetta."""
    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", src,
         "-ar", "16000", "-ac", "1", "-f", "wav", dst],
        check=True,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8013")))
