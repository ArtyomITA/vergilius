"""Prove del punto 4 (Smart Turn v3): voce/fine_turno.py e la regola a due
soglie in voce/asr_streaming.py, piu' il ponte a leva spenta.

Il tts-venv non ha pytest: asserzioni in fila, una riga per prova, codice di
uscita 1 se almeno una fallisce.

    tts-venv\\Scripts\\python.exe scripts\\prova_fine_turno.py
    ... --veloce     salta la prova con sherpa vero (circa 40 s e 700 MB di RAM)

Cosa si prova (piano v5, punto 4):
  1. coda tagliata a 0,2 s +-10 ms su segnale sintetico
  2. audio < 8 s -> zeri in testa, > 8 s -> ultimi 8 s; feature [1, 80, 800]
  3. sha sbagliato o file assente -> Smart Turn spento, regola di oggi
  4. eccezione del modello -> regola di oggi
  5. tabella delle decisioni con predittore finto (p=0,9 senza punto chiude al
     campanello; p=0,1 col punto aspetta ATTESA; p=0,5 col punto chiude), una
     inferenza per campanello, audio del turno al massimo 8 s e azzerato
  6. feature numpy contro le fixture di transformers (scripts/fixture_fine_turno,
     prodotte in D:/vergilius-lab/venv-banco): max |diff| <= 1e-3, |diff p| <= 0,01
  7. leva spenta -> eventi del websocket identici a oggi su
     voice-samples/campione_nuovo_16k.wav (se c'e')
"""

import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "voce"))

import asr_streaming  # noqa: E402
import fine_turno  # noqa: E402

FIXTURE = RADICE / "scripts" / "fixture_fine_turno"
CAMPIONE = RADICE / "voice-samples" / "campione_nuovo_16k.wav"
SR = 16000
PEZZO = 1600  # 100 ms, come asrWorklet.js

_esiti = []


def prova(nome, condizione, dettaglio=""):
    _esiti.append((nome, bool(condizione)))
    print(f"[{'ok' if condizione else 'NO'}] {nome}" + (f"  ({dettaglio})" if dettaglio else ""))


# -- segnali sintetici (deterministici, senza generatore casuale) ----------------

def segnale_sintetico(secondi: float, frequenza: int = SR) -> np.ndarray:
    """Voce finta: armoniche su una fondamentale che oscilla, sillabe a 4 Hz,
    una pausa ogni 2 s e un fruscio pseudo-casuale da formula. Nessun
    generatore casuale, cosi' e' identico con ogni versione di numpy: le
    fixture di transformers sono calcolate su questo stesso segnale."""
    n = int(round(secondi * frequenza))
    t = np.arange(n, dtype=np.float64) / frequenza
    f0 = 140.0 + 25.0 * np.sin(2 * np.pi * 0.7 * t)
    fase = 2 * np.pi * np.cumsum(f0) / frequenza
    voce = sum((0.5 / k) * np.sin(k * fase) for k in range(1, 12))
    sillabe = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)
    pause = (np.mod(t, 2.0) < 1.6).astype(np.float64)
    fr = np.sin(np.arange(n, dtype=np.float64) * 12.9898) * 43758.5453
    fr = fr - np.floor(fr) - 0.5
    x = voce * sillabe * pause + 0.02 * fr
    return (0.3 * x / np.max(np.abs(x))).astype(np.float32)


def tono(secondi, db, f=220.0):
    t = np.arange(int(round(secondi * SR))) / SR
    return (10 ** (db / 20) * np.sqrt(2) * np.sin(2 * np.pi * f * t)).astype(np.float32)


def fruscio(secondi, db):
    n = int(round(secondi * SR))
    fr = np.sin(np.arange(n, dtype=np.float64) * 78.233) * 12345.678
    fr = (fr - np.floor(fr) - 0.5) * np.sqrt(12)  # varianza 1
    return (10 ** (db / 20) * fr).astype(np.float32)


# -- riconoscitore e predittore finti --------------------------------------------

class _FlussoFinto:
    def __init__(self, rec):
        self.rec = rec

    def set_option(self, *_):
        pass

    def accept_waveform(self, _sr, _campioni):
        self.rec.i += 1

    def input_finished(self):
        pass


class RiconoscitoreFinto:
    """Copione: una coppia (testo, campanello) per ogni pezzo accettato."""

    def __init__(self, copione):
        self.copione = list(copione)
        self.i = -1

    def create_stream(self):
        return _FlussoFinto(self)

    def is_ready(self, _s):
        return False

    def decode_stream(self, _s):
        pass

    def get_result(self, _s):
        return self.copione[self.i][0] if 0 <= self.i < len(self.copione) else ""

    def is_endpoint(self, _s):
        return self.copione[self.i][1] if 0 <= self.i < len(self.copione) else False

    def reset(self, _s):
        pass


class PredittoreFinto:
    def __init__(self, p=None, errore=False):
        self.p = p
        self.errore = errore
        self.chiamate = 0
        self.lunghezze = []

    def probabilita(self, audio):
        self.chiamate += 1
        self.lunghezze.append(len(audio))
        if self.errore:
            raise RuntimeError("modello rotto per prova")
        return self.p


class SessioneOggi(asr_streaming.Sessione):
    """La regola di oggi, copiata alla lettera da voce/asr_streaming.py prima
    del punto 4 (git HEAD fd9160f): il riferimento contro cui si confronta."""

    def _fine_turno(self, testo: str, durata_pezzo: float) -> bool:
        if not self.rec.is_endpoint(self.stream):
            self._candidato = None
            self._silenzio_dopo = 0.0
            return False

        if not testo.strip():
            self._candidato = None
            self._silenzio_dopo = 0.0
            return True

        if testo.rstrip().endswith(asr_streaming.FINE_FRASE):
            self._candidato = None
            self._silenzio_dopo = 0.0
            return True

        if self._candidato != testo:
            self._candidato = testo
            self._silenzio_dopo = 0.0
            return False

        self._silenzio_dopo += durata_pezzo
        if self._silenzio_dopo >= (asr_streaming.SILENZIO_FINE_TURNO_LUNGO
                                   - asr_streaming.SILENZIO_FINE_TURNO):
            self._candidato = None
            self._silenzio_dopo = 0.0
            return True
        return False


def copione(testo, parlato=10, silenzio=30):
    """`parlato` pezzi senza campanello, poi `silenzio` pezzi col campanello."""
    return [(testo, False)] * parlato + [(testo, True)] * silenzio


def primo_fine(classe, righe, smart=None, attivo=True, **leve):
    """Indice del primo pezzo che chiude il turno (None se non chiude)."""
    salvate = {k: getattr(asr_streaming, k) for k in
               ("carica", "_smart_turn", "SMART_TURN", "SMART_TURN_ALTA",
                "SMART_TURN_BASSA", "SMART_TURN_ATTESA")}
    rec = RiconoscitoreFinto(righe)
    try:
        asr_streaming.carica = lambda: rec
        asr_streaming._smart_turn = lambda: smart
        asr_streaming.SMART_TURN = attivo
        for k, v in leve.items():
            setattr(asr_streaming, k, v)
        s = classe("it")
        for i in range(len(righe)):
            _, _, fine = s.aggiungi(np.full(PEZZO, 0.01, np.float32))
            if fine:
                return i, s
        return None, s
    finally:
        for k, v in salvate.items():
            setattr(asr_streaming, k, v)


class _Raccogli(logging.Handler):
    def __init__(self):
        super().__init__()
        self.righe = []

    def emit(self, record):
        self.righe.append(record.getMessage())


# -- prove ----------------------------------------------------------------------

def prova_taglio_coda():
    for coda in (0.2, 0.5):
        a = np.concatenate([fruscio(0.3, -70), tono(1.0, -20), fruscio(1.5, -70)])
        tagliato, silenzio = fine_turno.taglia_coda(a, coda)
        atteso = 0.3 + 1.0 + coda
        prova(f"coda tagliata a {coda} s +-10 ms", abs(len(tagliato) / SR - atteso) <= 0.010,
              f"durata {len(tagliato) / SR:.3f} s, attesa {atteso:.3f}")
        prova(f"silenzio in coda misurato (coda {coda})", abs(silenzio - 1.5) <= 0.010,
              f"{silenzio:.3f} s")
    corto = np.concatenate([tono(1.0, -20), fruscio(0.1, -70)])
    tagliato, _ = fine_turno.taglia_coda(corto, 0.2)
    prova("coda piu' corta di CODA resta intera", len(tagliato) == len(corto))
    muto = np.zeros(SR, np.float32)
    tagliato, silenzio = fine_turno.taglia_coda(muto, 0.2)
    prova("audio muto non si taglia", len(tagliato) == SR and silenzio == 0.0)


def prova_finestra():
    a = segnale_sintetico(3.0)
    p = fine_turno.prepara(a)
    n0 = fine_turno.CAMPIONI - len(a)
    prova("< 8 s: zeri in testa", len(p) == fine_turno.CAMPIONI and not p[:n0].any()
          and np.array_equal(p[n0:], a))
    b = segnale_sintetico(9.5)
    p = fine_turno.prepara(b)
    prova("> 8 s: ultimi 8 s", len(p) == fine_turno.CAMPIONI and np.array_equal(p, b[-fine_turno.CAMPIONI:]))
    f = fine_turno.log_mel(a)
    prova("feature [1, 80, 800] float32", f.shape == (1, 80, 800) and f.dtype == np.float32)


def prova_sha_e_assente():
    modello = fine_turno.MODELLO_PREDEFINITO
    if not modello.is_file():
        prova("sha sbagliato -> spento (manca il modello, salto)", True)
        return
    with tempfile.TemporaryDirectory() as d:
        falso = Path(d) / modello.name
        shutil.copyfile(modello, falso)
        dati = bytearray(falso.read_bytes())
        dati[-1] ^= 0xFF
        falso.write_bytes(bytes(dati))
        try:
            fine_turno.FineTurno(falso)
            prova("sha sbagliato -> ModelloNonValido", False)
        except fine_turno.ModelloNonValido as e:
            prova("sha sbagliato -> ModelloNonValido", "sha256" in str(e))
        # carica() con file alterato: None, una riga nel log, regola di oggi.
        vecchi = fine_turno._istanza, fine_turno._tentato
        fine_turno._istanza, fine_turno._tentato = None, False
        try:
            prova("sha sbagliato -> carica() = None (spento)", fine_turno.carica(falso) is None)
            fine_turno._istanza, fine_turno._tentato = None, False
            prova("file assente -> carica() = None", fine_turno.carica(Path(d) / "manca.onnx") is None)
        finally:
            fine_turno._istanza, fine_turno._tentato = vecchi
    # Sessione a leva accesa con predittore spento: stesso primo_fine di oggi.
    for testo in ("Ciao come stai.", "ciao come"):
        oggi, _ = primo_fine(SessioneOggi, copione(testo), attivo=False)
        spento, s = primo_fine(asr_streaming.Sessione, copione(testo), smart=None, attivo=True)
        prova(f"predittore spento = regola di oggi ({testo!r})", oggi == spento and s._smart is None,
              f"oggi {oggi}, leva accesa senza modello {spento}")


def prova_eccezione():
    for testo in ("Ciao come stai.", "ciao come"):
        oggi, _ = primo_fine(SessioneOggi, copione(testo), attivo=False)
        rotto = PredittoreFinto(errore=True)
        esito, _ = primo_fine(asr_streaming.Sessione, copione(testo), smart=rotto,
                              SMART_TURN_ATTESA=2.0)
        prova(f"eccezione del modello -> regola di oggi ({testo!r})",
              esito == oggi and rotto.chiamate == 1, f"oggi {oggi}, con errore {esito}")


def prova_tabella():
    campanello = 10
    attesa_oggi, _ = primo_fine(SessioneOggi, copione("ciao come"), attivo=False)
    casi = [
        # (p, testo, ATTESA, pezzo atteso, cosa)
        (0.9, "ciao come", 1.2, campanello, "p=0,9 senza punto -> chiude al campanello"),
        (0.1, "Ciao come stai.", 1.2, attesa_oggi, "p=0,1 col punto -> aspetta ATTESA 1,2"),
        (0.1, "Ciao come stai.", 2.0, campanello + 16, "p=0,1 col punto -> aspetta ATTESA 2,0"),
        (0.5, "Ciao come stai.", 1.2, campanello, "p=0,5 col punto -> chiude"),
        (0.5, "ciao come", 1.2, attesa_oggi, "p=0,5 senza punto -> aspetta (ALTA 0,7)"),
        (0.7, "ciao come", 1.2, campanello, "p=0,7 senza punto -> chiude (>= ALTA)"),
        (0.2, "Ciao come stai.", 1.2, campanello, "p=0,2 col punto -> chiude (>= BASSA)"),
    ]
    for p, testo, attesa, atteso, cosa in casi:
        finto = PredittoreFinto(p)
        esito, _ = primo_fine(asr_streaming.Sessione, copione(testo), smart=finto,
                              SMART_TURN_ALTA=0.7, SMART_TURN_BASSA=0.2, SMART_TURN_ATTESA=attesa)
        prova(cosa, esito == atteso and finto.chiamate == 1,
              f"pezzo {esito}, atteso {atteso}, inferenze {finto.chiamate}")
    prova("ATTESA 1,2 = attesa di oggi (0,75 s dopo il campanello)", attesa_oggi == campanello + 8,
          f"pezzo {attesa_oggi}")

    # Ripresa a parlare durante l'attesa: nuovo campanello, nuova inferenza.
    righe = copione("ciao come", 10, 4) + copione("ciao come stai", 5, 30)
    finto = PredittoreFinto(0.5)
    esito, _ = primo_fine(asr_streaming.Sessione, righe, smart=finto, SMART_TURN_ATTESA=1.2)
    prova("ripresa durante l'attesa -> un'inferenza per campanello", finto.chiamate == 2
          and esito == 10 + 4 + 5 + 8, f"inferenze {finto.chiamate}, pezzo {esito}")

    # Audio del turno: al massimo 8 s, azzerato in chiudi_turno, e il predittore
    # riceve l'audio tagliato in coda.
    righe = [("parla", False)] * 100 + [("parla", True)] * 5
    finto = PredittoreFinto(0.9)
    esito, s = primo_fine(asr_streaming.Sessione, righe, smart=finto)
    prova("audio del turno <= 8 s", len(s.audio_turno()) == 8 * SR and s._audio_n <= 8 * SR + PEZZO,
          f"{len(s.audio_turno()) / SR:.1f} s tenuti")
    s.chiudi_turno()
    prova("audio azzerato in chiudi_turno", len(s.audio_turno()) == 0 and s._audio_n == 0)

    # Leva spenta: niente audio tenuto, niente predittore.
    esito, s = primo_fine(asr_streaming.Sessione, copione("ciao come"), smart=PredittoreFinto(0.9),
                          attivo=False)
    prova("leva spenta: nessun audio tenuto, nessun predittore", s._smart is None and s._audio_n == 0
          and esito == attesa_oggi)

    # Riga di log.
    raccogli = _Raccogli()
    logging.getLogger("asr-streaming").addHandler(raccogli)
    logging.getLogger("asr-streaming").setLevel(logging.INFO)
    try:
        primo_fine(asr_streaming.Sessione, copione("ciao come"), smart=PredittoreFinto(0.9))
    finally:
        logging.getLogger("asr-streaming").removeHandler(raccogli)
    riga = next((r for r in raccogli.righe if r.startswith("[fine-turno] p=")), "")
    prova("log [fine-turno] p ms punto decisione silenzio",
          all(k in riga for k in ("p=0.900", "ms=", "punto=no", "decisione=chiude", "silenzio=")), riga)


def prova_fixture():
    rif_json = FIXTURE / "riferimento.json"
    if not rif_json.is_file():
        prova("fixture di transformers presenti", False, f"manca {rif_json}")
        return
    rif = json.loads(rif_json.read_text(encoding="utf-8"))
    modello = fine_turno.FineTurno() if fine_turno.MODELLO_PREDEFINITO.is_file() else None
    prova("modello ufficiale: sha giusto, si carica", modello is not None)
    for nome, dati in rif["fixture"].items():
        audio = segnale_sintetico(dati["secondi"])
        mia = fine_turno.log_mel(audio)
        loro = np.load(FIXTURE / f"{nome}.npy")
        diff = float(np.abs(mia[0] - loro).max())
        prova(f"{nome}: feature numpy = transformers (<= 1e-3)", diff <= 1e-3, f"max |diff| {diff:.2e}")
        if modello is not None:
            dp = abs(modello.probabilita_da_feature(mia) - dati["p_transformers"])
            prova(f"{nome}: |diff p| <= 0,01", dp <= 0.01, f"{dp:.2e}")


def prova_leva_spenta_ponte():
    if not CAMPIONE.is_file() or not asr_streaming.disponibile():
        prova("leva spenta -> eventi identici (manca campione o sherpa, salto)", True)
        return
    import soundfile as sf
    from fastapi.testclient import TestClient

    import ponte_voce

    a, sr = sf.read(str(CAMPIONE), dtype="int16")
    assert sr == SR and a.ndim == 1
    # Pausa lunga in mezzo e silenzio in fondo: piu' di un turno nella prova.
    zeri = np.zeros(int(2.0 * SR), np.int16)
    a = np.concatenate([a[:9 * SR], zeri, a[9 * SR:], zeri, zeri])
    pezzi = [a[i:i + PEZZO].tobytes() for i in range(0, len(a), PEZZO)]

    assert not asr_streaming.SMART_TURN, "la prova va fatta con ASR_SMART_TURN spenta"
    chiamato = []
    originale = asr_streaming._smart_turn
    asr_streaming._smart_turn = lambda: chiamato.append(1)
    try:
        # Senza "with": gli eventi di avvio (riscaldamento della sintesi) non partono.
        client = TestClient(ponte_voce.app)
        eventi = []
        with client.websocket_connect("/v1/audio/stream?lingua=it") as ws:
            for dati in pezzi:
                ws.send_bytes(dati)
            ws.send_text("fine")
            while True:
                m = ws.receive_json()
                eventi.append(m)
                if m.get("chiuso") or m.get("errore"):
                    break
    finally:
        asr_streaming._smart_turn = originale

    s = SessioneOggi("it")
    oggi = []
    for dati in pezzi:
        testo, cambiato, fine = s.aggiungi(asr_streaming.da_pcm16(dati))
        if fine:
            oggi.append({"testo": s.chiudi_turno(), "fine_turno": True})
        elif cambiato:
            oggi.append({"testo": testo, "fine_turno": False})
    oggi.append({"testo": s.finito(), "fine_turno": True, "chiuso": True})

    turni = sum(1 for e in oggi if e.get("fine_turno") and not e.get("chiuso"))
    prova("leva spenta -> eventi del ponte identici a oggi (campione_nuovo_16k)",
          eventi == oggi and not chiamato,
          f"{len(eventi)} eventi, {turni} fine turno, Smart Turn chiamato {len(chiamato)} volte")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)
    veloce = "--veloce" in sys.argv
    prova_taglio_coda()
    prova_finestra()
    prova_sha_e_assente()
    prova_eccezione()
    prova_tabella()
    prova_fixture()
    if not veloce:
        prova_leva_spenta_ponte()
    falliti = [n for n, ok in _esiti if not ok]
    print(f"\n{len(_esiti) - len(falliti)}/{len(_esiti)} prove passate")
    for n in falliti:
        print(f"  FALLITA: {n}")
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
