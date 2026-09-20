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
import re
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

# PocketTTS taglia il testo in pezzi da MAX_TOKEN_PER_CHUNK=50 token e oltre
# quella soglia SALTA le parole in silenzio ("Chunk has 182 tokens (max 50),
# generation may skip words" in voce/pockettts.log). Il suo spezzatore interno
# (pocket_tts/models/tts_model.py, split_into_best_sentences) sa dividere solo
# su ".!?" e poi su ",;:": un elenco senza punteggiatura resta un pezzo solo,
# lungo quanto arriva.
#
# Misurato col suo stesso tokenizer sentencepiece su italiano: 0,46 token per
# carattere, quindi 50 token sono ~108 caratteri, non 190. Il vecchio valore
# (e il suo commento "~45 token") sbagliava di un fattore due, e siccome era
# sopra i 180 del browser non proteggeva niente.
LIMITE_PEZZO = 105
# Il PRIMO pezzo e' l'unico la cui attesa si sente come silenzio dopo la
# risposta: si chiude alla prima clausola utile (tipicamente 15-60 caratteri),
# cosi' la voce parte prima. Sotto MIN_PRIMO_PEZZO il taglio non vale la
# richiesta in piu' e la voce suona mozzata. Se in testa non c'e' nessun taglio
# naturale si torna al limite normale invece di spezzare a caso.
LIMITE_PRIMO_PEZZO = 60
MIN_PRIMO_PEZZO = 12
# Intestazione WAV canonica scritta dal modulo `wave`: RIFF + fmt + data.
INTESTAZIONE_WAV = 44

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
    # Accettata per compatibilita' con il formato OpenAI e basta: PocketTTS non
    # ha nessun parametro di velocita'. Chi vuole l'effetto lo applica in
    # riproduzione (static/js/tts-ai.js, _applicaVelocita).
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


# -- preparazione del testo ---------------------------------------------

# Emoji e pittogrammi. Niente \p{...}: il modulo `re` non li conosce, quindi si
# elencano gli intervalli. I numeri e il cancelletto restano fuori di proposito:
# toglierli vorrebbe dire perdere ogni cifra della risposta.
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿"
    "︀-️‍⃣]"
)
_URL = re.compile(r"(?:https?://|www\.)\S+")
# Marcature fra parentesi quadre che NON si leggono: `[joy]`, `[sad]`,
# `[emotion:happy]`, `[pausa]`, `[TOOL_CALL]`. `avatarPersona.js` chiede al
# modello di metterle in testa a ogni risposta; la regola generica che
# trasforma le parentesi in spazi lasciava dentro la parola, e l'assistente
# diceva "joy" prima di ogni frase. Si tolgono solo le etichette corte e senza
# spazi interni: "[vedi la nota in fondo]" resta una frase. E si accettano solo
# le forme che un tag ha davvero (tutto minuscolo, tutto maiuscolo, oppure con
# i due punti), cosi' "[Milano]" o "[2024]" restano quello che sono.
_TAG_QUADRE = re.compile(
    r"\[\s*(?:[a-z][a-z0-9_.\-]{0,20}|[A-Z][A-Z0-9_.\-]{0,20})"
    r"(?:\s*[:=]\s*[A-Za-z0-9_.\- ]{0,20})?\s*\]")


def pulisci_per_voce(testo: str) -> str:
    """Toglie quello che non si legge ad alta voce.

    Rifa' lato server l'essenziale di quello che `forSpeech`/`extractPlainText`
    gia' fanno nel browser (static/js/tts-ai.js): ragionamento, blocchi di
    codice, indirizzi, markdown, emoji. Serve a chi arriva qui senza passare dal
    browser — altrimenti il modello si mette a dire "asterisco asterisco" e a
    scandire gli indirizzi carattere per carattere.
    """
    if not testo:
        return ""
    t = re.sub(r"<think(?:ing)?\b[^>]*>.*?</think(?:ing)?>", " ", testo,
               flags=re.I | re.S)
    t = re.sub(r"<think(?:ing)?\b[^>]*>.*$", " ", t, flags=re.I | re.S)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)      # blocchi di codice chiusi
    t = re.sub(r"```.*$", " ", t, flags=re.S)         # e quello ancora aperto
    t = _URL.sub(" ", t)
    t = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", t)         # link markdown: resta la scritta
    t = _TAG_QUADRE.sub(" ", t)                       # [joy], [emotion:happy], [1]
    t = _EMOJI.sub("", t)
    t = re.sub(r"^[ \t]*[-*+•]\s+", "", t, flags=re.M)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"[()\[\]{}<>«»„“”\"']", " ", t)       # parentesi via, contenuto resta
    t = re.sub(r"[|_*~`^]", " ", t)
    t = re.sub(r"[ \t]+([,.;:!?])", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# Punteggiatura buona per tagliare SOLO quando e' seguita da spazio o da fine
# testo. E' la regola che tiene insieme "1.541,19", "3,5%" e "LDO.MI": li'
# dopo il punto e dopo la virgola c'e' una cifra o una lettera, non uno spazio.
_FINE_FRASE = re.compile(r"[.!?…]+(?=\s|$)")
_PAUSA_FORTE = re.compile(r"[;:](?=\s|$)")
_VIRGOLA = re.compile(r",(?=\s|$)")
# Prima di una congiunzione si respira senza che si senta il taglio. Si taglia
# PRIMA della parola, non dopo.
_CONGIUNZIONE = re.compile(
    r"\s+(?=(?:e|ed|o|oppure|ma|pero'|però|mentre|quindi|percio'|perciò|"
    r"perche'|perché|poi|che|se|con|per|anche|dove|quando|come)\s)")


def _dicibile(pezzo: str) -> bool:
    """Un pezzo senza lettere ne' cifre e' solo punteggiatura: mandarlo alla
    sintesi vuol dire pagare una richiesta per un silenzio."""
    return any(c.isalnum() for c in pezzo)


def _taglio_naturale(testo: str, tetto: int, minimo: int) -> int:
    """Dove tagliare `testo` (estremo escluso) restando entro `tetto`.

    Ordine di preferenza: fine frase, punto e virgola/due punti, virgola,
    congiunzione. Restituisce 0 se nessun taglio naturale cade nella finestra.
    """
    for rx, dopo in ((_FINE_FRASE, True), (_PAUSA_FORTE, True),
                     (_VIRGOLA, True), (_CONGIUNZIONE, False)):
        migliore = 0
        for m in rx.finditer(testo):
            pos = m.end() if dopo else m.start()
            if pos > tetto:
                break
            if minimo <= pos < len(testo):
                migliore = pos
        if migliore:
            return migliore
    return 0


def _taglio_su_spazio(testo: str, tetto: int) -> int:
    """Ultimo spazio dentro il tetto. Mai a meta' parola: se la prima parola e'
    gia' piu' lunga del tetto la si lascia intera e si sfora."""
    pos = testo.rfind(" ", 0, tetto + 1)
    if pos > 0:
        return pos
    pos = testo.find(" ")
    return pos if pos > 0 else len(testo)


def spezza_per_sintesi(testo: str, limite: int = LIMITE_PEZZO,
                       limite_primo: int = LIMITE_PRIMO_PEZZO) -> list[str]:
    """Taglia il testo in pezzi che PocketTTS sa dire per intero.

    Quattro tagli in ordine di preferenza (fine frase, punto e virgola/due
    punti, virgola, congiunzione) e in ultima istanza lo spazio piu' vicino.
    Mai a meta' parola, mai un pezzo vuoto o di sola punteggiatura, mai dentro
    un numero o una sigla. Il primo pezzo si chiude prima degli altri: e'
    l'unico la cui attesa l'utente sente come silenzio.
    """
    if not testo:
        return []

    resto = " ".join(testo.split())
    pezzi: list[str] = []
    while resto:
        primo = not pezzi
        tetto = limite_primo if primo else limite
        if len(resto) <= tetto:
            pezzi.append(resto)
            break

        taglio = _taglio_naturale(
            resto, tetto, MIN_PRIMO_PEZZO if primo else max(1, limite // 3))
        if primo and not taglio:
            # Nessuna clausola breve in testa: si riprova col limite normale
            # invece di spezzare a caso la prima frase.
            tetto = limite
            if len(resto) <= tetto:
                pezzi.append(resto)
                break
            taglio = _taglio_naturale(resto, tetto, max(1, limite // 3))
        if not taglio:
            taglio = _taglio_su_spazio(resto, tetto)

        pezzo, resto = resto[:taglio].strip(), resto[taglio:].strip()
        if _dicibile(pezzo):
            pezzi.append(pezzo)
        elif pezzi:
            # Punteggiatura orfana: si attacca al pezzo precedente, non si manda.
            pezzi[-1] = (pezzi[-1] + pezzo).strip()

    # Riunione dei pezzi troppo corti: una richiesta in meno e' mezzo secondo
    # in meno. Il primo resta com'e', altrimenti si perde l'anticipo.
    uniti: list[str] = []
    for p in pezzi:
        if len(uniti) > 1 and len(uniti[-1]) + 1 + len(p) <= limite:
            uniti[-1] = uniti[-1] + " " + p
        else:
            uniti.append(p)
    return [p for p in uniti if _dicibile(p)]


def intestazione_in_streaming(testa: bytes) -> bytes:
    """Rimette a posto le due lunghezze dell'intestazione WAV.

    PocketTTS dichiara un miliardo di campioni (tts_model/audio.py: setnframes
    1_000_000_000) e non ritocca mai l'intestazione, perche' il flusso non e'
    riavvolgibile. Nel browser quel file dura undici ore: `duration` non serve a
    niente e l'elemento continua ad aspettare byte che non arrivano piu'.
    0xFFFFFFFF e' la convenzione dei flussi WAV di lunghezza ignota e i lettori
    la trattano come tale: durata infinita, fine quando la connessione chiude.
    Qui non si puo' scrivere la lunghezza vera: sarebbe nota solo alla fine, e
    aspettare la fine costa tutta la sintesi (2 s) al posto dei 150 ms attuali.
    """
    if len(testa) < INTESTAZIONE_WAV or testa[:4] != b"RIFF" or testa[36:40] != b"data":
        return testa
    ignota = b"\xff\xff\xff\xff"
    return testa[:4] + ignota + testa[8:40] + ignota + testa[44:]


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
    text = pulisci_per_voce(req.input or "")
    if not text:
        raise HTTPException(400, "input vuoto")

    pezzi = spezza_per_sintesi(text)
    if not pezzi:
        # Testo fatto solo di punteggiatura, tag o emoji: dopo la pulizia non
        # resta niente da dire e PocketTTS risponderebbe 4xx a meta' coda.
        raise HTTPException(400, "input senza niente da dire")
    voce = req.voice or DEFAULT_VOICE
    client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))

    async def apri(testo: str):
        # Unico punto del ponte da cui parte del testo per PocketTTS (l'altro
        # e' il riscaldamento, che manda una parola sola). Se un pezzo arriva
        # qui piu' lungo del limite, lo spezzatore e' stato aggirato: si scrive
        # nel log, altrimenti le parole saltate restano invisibili.
        if len(testo) > LIMITE_PEZZO:
            logger.warning("pezzo di %d caratteri verso PocketTTS (limite %d): "
                           "spezzatore aggirato, PocketTTS saltera' parole",
                           len(testo), LIMITE_PEZZO)
        richiesta = client.build_request(
            "POST", POCKETTTS_URL, data={"text": testo, "voice_url": voce},
        )
        return await client.send(richiesta, stream=True)

    # La prima richiesta si fa qui, non dentro il generatore: e' l'unico punto
    # in cui si puo' ancora rispondere con un codice di errore invece che con
    # mezzo file WAV.
    try:
        risposta = await apri(pezzi[0])
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
        #
        # I pezzi escono in fila e diventano UN solo file: si tiene
        # l'intestazione del primo (corretta nelle lunghezze) e si buttano le 44
        # byte di quelle dei pezzi successivi, altrimenti in mezzo all'audio si
        # sentirebbe il fruscio dell'intestazione letta come campioni.
        corrente = risposta
        try:
            for indice, pezzo in enumerate(pezzi):
                if indice:
                    corrente = await apri(pezzo)
                    if corrente.status_code != 200:
                        logger.error("PocketTTS ha risposto %s sul pezzo %d/%d: "
                                     "il resto della frase va perso",
                                     corrente.status_code, indice + 1, len(pezzi))
                        await corrente.aclose()
                        return
                avanzo = b""
                tagliata = False
                async for blocco in corrente.aiter_bytes():
                    if not tagliata:
                        avanzo += blocco
                        if len(avanzo) < INTESTAZIONE_WAV:
                            continue
                        testa, blocco = avanzo[:INTESTAZIONE_WAV], avanzo[INTESTAZIONE_WAV:]
                        tagliata = True
                        if indice == 0:
                            yield intestazione_in_streaming(testa)
                        if not blocco:
                            continue
                    yield blocco
                await corrente.aclose()
        finally:
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
