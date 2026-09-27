"""Fine turno che ascolta la voce, non solo il silenzio (Smart Turn v3.2, CPU).

Smart Turn v3 di Pipecat (licenza BSD-2, vedi NOTICE.md): encoder Whisper Tiny
con una testa lineare, 8 MB in int8. Riceve gli ultimi 8 secondi del turno come
log-mel Whisper [1, 80, 800] e restituisce la probabilita' che chi parla abbia
finito (l'uscita e' gia' passata da una sigmoide).

Lo usa solo `asr_streaming.Sessione` al campanello di sherpa: una inferenza per
campanello, mai per pezzo. Se qualcosa non va (file assente, sha256 diverso,
onnxruntime che non parte, eccezione a meta') Smart Turn si spegne e resta la
regola di oggi: punteggiatura del parziale piu' attesa lunga.

Le feature si calcolano in numpy: transformers nel tts-venv non c'e' e non ci
deve entrare. La prova di equivalenza contro
WhisperFeatureExtractor(chunk_length=8, do_normalize=True) sta in
D:/vergilius-lab/ricerche/live/04-smart-turn-banco.md, le fixture in
scripts/fixture_fine_turno/ (le rilegge scripts/prova_fine_turno.py).
"""

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("asr-streaming")

FREQUENZA = 16000
SECONDI = 8
CAMPIONI = SECONDI * FREQUENZA          # 128000: finestra fissa del modello
N_FFT = 400                             # 25 ms
HOP = 160                               # 10 ms -> 800 fotogrammi in 8 s
N_MEL = 80

NOME_MODELLO = "smart-turn-v3.2-cpu.onnx"
# Hash del file ufficiale (Hugging Face pipecat-ai/smart-turn-v3, X-Linked-ETag):
# un file diverso non si carica, qualunque cosa ci sia dentro.
SHA256_ATTESO = "2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f"
MODELLO_PREDEFINITO = Path(__file__).resolve().parent.parent / "asr-models" / NOME_MODELLO


# -- log-mel Whisper in numpy -------------------------------------------------

def _hz_in_mel(f):
    """Scala mel "slaney" (quella di Whisper): lineare sotto 1 kHz, log sopra."""
    f = np.asarray(f, dtype=np.float64)
    mel = 3.0 * f / 200.0
    sopra = f >= 1000.0
    return np.where(sopra, 15.0 + np.log(np.maximum(f, 1e-10) / 1000.0) * (27.0 / np.log(6.4)), mel)


def _mel_in_hz(m):
    m = np.asarray(m, dtype=np.float64)
    f = 200.0 * m / 3.0
    sopra = m >= 15.0
    return np.where(sopra, 1000.0 * np.exp(np.log(6.4) / 27.0 * (m - 15.0)), f)


def _filtri_mel() -> np.ndarray:
    """Banco di 80 filtri triangolari da 0 a 8 kHz, normalizzati "slaney"
    (area costante), come mel_filter_bank di transformers. Forma (201, 80)."""
    n_bin = 1 + N_FFT // 2
    freq_fft = np.linspace(0, FREQUENZA // 2, n_bin)
    punti_mel = np.linspace(_hz_in_mel(0.0), _hz_in_mel(FREQUENZA / 2), N_MEL + 2)
    punti_hz = _mel_in_hz(punti_mel)
    larghezze = np.diff(punti_hz)
    pendenze = punti_hz[None, :] - freq_fft[:, None]
    discesa = -pendenze[:, :-2] / larghezze[:-1]
    salita = pendenze[:, 2:] / larghezze[1:]
    filtri = np.maximum(0.0, np.minimum(discesa, salita))
    filtri *= (2.0 / (punti_hz[2:N_MEL + 2] - punti_hz[:N_MEL]))[None, :]
    return filtri


_FILTRI = _filtri_mel()
# Hann periodica (non simmetrica): e' quella di torch.hann_window e di Whisper.
_FINESTRA = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(N_FFT) / N_FFT)


def prepara(audio) -> np.ndarray:
    """Esattamente 8 s: se l'audio e' piu' corto gli zeri vanno IN TESTA (il
    parlato resta in fondo, dove il modello guarda), se e' piu' lungo restano
    gli ultimi 8 s."""
    a = np.asarray(audio, dtype=np.float32).reshape(-1)
    if len(a) > CAMPIONI:
        return a[-CAMPIONI:]
    if len(a) < CAMPIONI:
        return np.pad(a, (CAMPIONI - len(a), 0))
    return a


def log_mel(audio) -> np.ndarray:
    """Feature di ingresso [1, 80, 800] float32.

    Stessi passi di WhisperFeatureExtractor(chunk_length=8, do_normalize=True):
    media zero e varianza uno su tutti gli 8 s (zeri di testa compresi, come fa
    il codice ufficiale che li aggiunge prima dell'estrattore), STFT centrata con
    riflessione, potenza, filtri mel, log10, ultimo fotogramma scartato, tetto
    dinamico di 8 (80 dB) e scala (x + 4) / 4."""
    a = prepara(audio).astype(np.float64)
    a = (a - a.mean()) / np.sqrt(a.var() + 1e-7)
    p = np.pad(a, (N_FFT // 2, N_FFT // 2), mode="reflect")
    n_fot = 1 + (len(p) - N_FFT) // HOP
    indici = np.arange(N_FFT)[None, :] + HOP * np.arange(n_fot)[:, None]
    spettro = np.abs(np.fft.rfft(p[indici] * _FINESTRA[None, :], n=N_FFT, axis=1)) ** 2
    mel = spettro @ _FILTRI                                   # (801, 80)
    ls = np.log10(np.maximum(mel, 1e-10)).T[:, :-1]           # (80, 800)
    ls = np.maximum(ls, ls.max() - 8.0)
    ls = (ls + 4.0) / 4.0
    return ls.astype(np.float32)[None]


def taglia_coda(audio, coda: float = 0.2, frequenza: int = FREQUENZA):
    """Toglie il silenzio in fondo lasciandone `coda` secondi dopo l'ultimo
    parlato. Al campanello sherpa ha gia' contato ~0,45 s di silenzio piu' il
    pezzo da 320 ms: con tanta coda il modello diventa instabile (misurato da
    ORECCHIO: 0,2-0,5 s stabile, 0,8-1,2 s no), Pipecat lo chiama dopo 0,2 s.

    Parlato = blocchi da 10 ms sopra max(-50 dBFS, p90 - 30 dB).
    Restituisce (audio tagliato, secondi di silenzio trovati in fondo)."""
    a = np.asarray(audio, dtype=np.float32).reshape(-1)
    blocco = int(0.01 * frequenza)
    n = len(a) // blocco
    if n == 0:
        return a, 0.0
    energia = np.sqrt((a[:n * blocco].astype(np.float64).reshape(n, blocco) ** 2).mean(axis=1))
    db = 20.0 * np.log10(energia + 1e-9)
    soglia = max(-50.0, float(np.percentile(db, 90)) - 30.0)
    voce = np.nonzero(db > soglia)[0]
    if len(voce) == 0:
        # Nessun parlato riconoscibile: non si taglia niente.
        return a, 0.0
    fine_voce = (int(voce[-1]) + 1) * blocco
    fine = min(len(a), fine_voce + int(round(coda * frequenza)))
    return a[:fine], (len(a) - fine_voce) / frequenza


# -- modello ------------------------------------------------------------------

def sha256_file(percorso) -> str:
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for pezzo in iter(lambda: f.read(1 << 20), b""):
            h.update(pezzo)
    return h.hexdigest()


class ModelloNonValido(RuntimeError):
    """File assente o diverso da quello atteso: Smart Turn resta spento."""


class FineTurno:
    """Sessione onnxruntime su CPU. `probabilita(audio)` = p(turno finito)."""

    def __init__(self, percorso=None, thread: int = 1, sha_atteso: str = SHA256_ATTESO):
        self.percorso = Path(percorso or MODELLO_PREDEFINITO)
        if not self.percorso.is_file():
            raise ModelloNonValido(f"modello assente: {self.percorso}")
        sha = sha256_file(self.percorso)
        if sha != sha_atteso:
            raise ModelloNonValido(
                f"sha256 diverso da quello atteso ({sha[:16]}... invece di {sha_atteso[:16]}...)")
        import onnxruntime as ort

        opzioni = ort.SessionOptions()
        # Un thread di default: il modello costa 90-190 ms e i core servono a
        # sherpa, alla sintesi e a llama.cpp.
        opzioni.intra_op_num_threads = max(1, int(thread))
        opzioni.inter_op_num_threads = 1
        opzioni.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opzioni.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.thread = opzioni.intra_op_num_threads
        self._sessione = ort.InferenceSession(str(self.percorso), sess_options=opzioni,
                                              providers=["CPUExecutionProvider"])
        self._ingresso = self._sessione.get_inputs()[0].name

    def probabilita_da_feature(self, feature: np.ndarray) -> float:
        uscita = self._sessione.run(None, {self._ingresso: feature})[0]
        p = float(np.asarray(uscita).reshape(-1)[0])
        if not np.isfinite(p):
            raise ValueError(f"probabilita' non finita: {p}")
        return p

    def probabilita(self, audio) -> float:
        return self.probabilita_da_feature(log_mel(audio))


_istanza: Optional[FineTurno] = None
_tentato = False
_lucchetto = threading.Lock()


def carica(percorso=None, thread: int = 1) -> Optional[FineTurno]:
    """Carica Smart Turn una volta per processo. None se non puo' partire:
    il motivo si scrive nel log UNA volta e da li' vale la regola di oggi."""
    global _istanza, _tentato
    if _istanza is not None or _tentato:
        return _istanza
    with _lucchetto:
        if _istanza is not None or _tentato:
            return _istanza
        _tentato = True
        t0 = time.perf_counter()
        try:
            _istanza = FineTurno(percorso, thread)
            logger.info("[fine-turno] Smart Turn pronto: %s, %d thread, %.0f ms",
                        _istanza.percorso.name, _istanza.thread,
                        (time.perf_counter() - t0) * 1000)
        except Exception as e:  # noqa: BLE001
            _istanza = None
            logger.error("[fine-turno] Smart Turn SPENTO, resta la regola di oggi: %s: %s",
                         type(e).__name__, e)
    return _istanza
