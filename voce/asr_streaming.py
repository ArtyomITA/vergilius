"""Trascrizione mentre si parla, su CPU.

Nemotron-3.5-ASR-streaming 0.6B via sherpa-onnx: 40 lingue-locali, ONNX INT8,
nessuna VRAM. Sostituisce il giro precedente (registra tutto -> carica il file
-> ffmpeg -> Parakeet), che non produceva una parola finche' non premevi stop.

Due cose importanti che porta con se':

  * il testo arriva **mentre** parli, quindi il modello puo' iniziare a leggere
    prima che tu abbia finito;
  * la **fine turno** e' automatica (`is_endpoint`), quindi il pulsante non
    serve piu'. Misurato: scatta ~800 ms dopo l'ultima parola con
    `rule2_min_trailing_silence=0.5`.

Il modello si carica una volta sola per processo: ~5 secondi e ~700 MB. Tenerlo
pigro renderebbe la prima frase della sessione inutilizzabile, quindi si scalda
all'avvio del ponte.
"""

import logging
import os
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger("asr-streaming")

CARTELLA = os.getenv(
    "ASR_MODELLO",
    "d:/assistenteeee/asr-models/"
    "sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-320ms-int8-2026-06-11",
)
LINGUA_PREDEFINITA = os.getenv("ASR_LINGUA", "it")
# 2 thread bastano: misurato RTF 0.5, cioe' meta' del tempo reale. Alzarlo
# ruberebbe core a llama.cpp senza servire.
THREAD = int(os.getenv("ASR_THREAD", "2"))
# Silenzio dopo il quale il turno si considera finito. 0.5 -> ~800 ms reali,
# contando il pezzo da 320 ms del modello.
SILENZIO_FINE_TURNO = float(os.getenv("ASR_SILENZIO", "0.5"))

FREQUENZA = 16000

_riconoscitore = None
_lucchetto = threading.Lock()


def disponibile() -> bool:
    if not os.path.isdir(CARTELLA):
        return False
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return False
    return True


def carica():
    """Costruisce il riconoscitore. Idempotente, e protetto: due richieste in
    arrivo insieme non devono caricare due volte 700 MB."""
    global _riconoscitore
    if _riconoscitore is not None:
        return _riconoscitore
    with _lucchetto:
        if _riconoscitore is not None:
            return _riconoscitore
        import sherpa_onnx

        logger.info("carico il modello di trascrizione in streaming...")
        _riconoscitore = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=f"{CARTELLA}/tokens.txt",
            encoder=f"{CARTELLA}/encoder.int8.onnx",
            decoder=f"{CARTELLA}/decoder.int8.onnx",
            joiner=f"{CARTELLA}/joiner.int8.onnx",
            num_threads=THREAD,
            provider="cpu",
            model_type="nemo_transducer",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=SILENZIO_FINE_TURNO,
            rule3_min_utterance_length=30.0,
        )
        logger.info("modello di trascrizione pronto")
    return _riconoscitore


class Sessione:
    """Un microfono acceso. Si nutre di PCM a 16 kHz e sputa testo parziale."""

    def __init__(self, lingua: Optional[str] = None):
        self.rec = carica()
        self.stream = self.rec.create_stream()
        self.lingua = lingua or LINGUA_PREDEFINITA
        try:
            # Il 3.5 e' multilingua con riconoscimento automatico; dichiarare la
            # lingua migliora la precisione. "auto" la lascia decidere a lui.
            self.stream.set_option("language", self.lingua)
        except Exception as e:
            logger.warning("lingua non impostabile (%s), resta automatica", e)
        self._ultimo = ""

    def aggiungi(self, campioni: np.ndarray):
        """Restituisce (testo, cambiato, fine_turno)."""
        self.stream.accept_waveform(FREQUENZA, campioni)
        while self.rec.is_ready(self.stream):
            self.rec.decode_stream(self.stream)

        testo = self.rec.get_result(self.stream)
        cambiato = testo != self._ultimo
        self._ultimo = testo

        fine = self.rec.is_endpoint(self.stream)
        return testo, cambiato, fine

    def chiudi_turno(self) -> str:
        """Chiude l'enunciato corrente e prepara il flusso per il prossimo,
        senza ricostruirlo: ricostruire lo stream perderebbe il riscaldamento
        dell'encoder e la prima frase del turno dopo ne uscirebbe peggio."""
        testo = self.rec.get_result(self.stream)
        self.rec.reset(self.stream)
        self._ultimo = ""
        return testo

    def finito(self) -> str:
        self.stream.input_finished()
        while self.rec.is_ready(self.stream):
            self.rec.decode_stream(self.stream)
        return self.rec.get_result(self.stream)


def da_pcm16(dati: bytes) -> np.ndarray:
    """I byte che manda il browser: interi con segno a 16 bit, little endian."""
    return np.frombuffer(dati, dtype="<i2").astype(np.float32) / 32768.0
