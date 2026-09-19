r"""Banco di prova della catena vocale, senza modello e senza GPU.

Recita la parte del modello: sputa una risposta italiana gia' scritta come se
fosse uno stream di token (con fase di ragionamento e un giro di strumento in
mezzo), la taglia con LE STESSE REGOLE del browser (static/js/tts-ai.js,
_spezza + colla dei frammenti corti) e manda ogni pezzo alla catena vocale vera.

Serve a rispondere a una domanda sola: quanto passa tra il primo token del
modello e il primo suono? E la voce sta al passo con il testo o si accumula
ritardo frase dopo frase?

Bersaglio scelto da solo, in ordine:
    1. Odysseus      http://127.0.0.1:7000/api/tts/stream?text=...
    2. ponte voce    http://127.0.0.1:8013/v1/audio/speech      (formato OpenAI)
    3. PocketTTS     http://127.0.0.1:8014/tts                  (multipart!)

Uso:   python scripts\prova-voce-pipeline.py [--tok-s 70] [--voce giovanni]

Non tocca la GPU, non avvia niente: quello che non e' acceso viene saltato.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# -- la battuta del "modello"--------------------------------------------
# Risposta tipica: apertura breve, elenco, chiusura. Niente markdown pesante,
# quello lo toglie gia' il browser prima di arrivare qui.
RAGIONAMENTO_S = 2.0        # fase "sta pensando": nessun testo, nessuna voce
PAUSA_STRUMENTO_S = 1.5     # giro di strumento a meta' risposta

RISPOSTA = (
    "Certo, ti riassumo la situazione. "
    "Il mercato di oggi si e' chiuso in leggero rialzo, trainato soprattutto "
    "dal settore tecnologico, mentre l'energia resta indietro. "
)
RISPOSTA_2 = (
    "Ho controllato anche il calendario: domani mattina hai due riunioni, "
    "la prima alle nove e trenta e la seconda subito dopo pranzo. "
    "Se vuoi posso spostare la seconda al pomeriggio, cosi' ti resta un'ora "
    "libera per finire il documento. Fammi sapere come preferisci procedere."
)

# -- regole di taglio, copiate da static/js/tts-ai.js--------------------
MIN_SPEAK_CHARS = 15
SUBSENTENCE_LOOKAHEAD = 25
MAX_SPEAK_CHARS = 180
DEBOUNCE_S = 0.150


MIN_FIRST_SPEAK_CHARS = 6


def spezza(regione: str, primo: bool = False) -> list[str]:
    """Porto fedele di AITTSManager._spezza()."""
    look = 0 if primo else SUBSENTENCE_LOOKAHEAD
    minimo = MIN_FIRST_SPEAK_CHARS if primo else MIN_SPEAK_CHARS
    pezzi, corrente = [], ""
    for i, ch in enumerate(regione):
        corrente += ch
        nxt = regione[i + 1] if i + 1 < len(regione) else ""
        resto = len(regione) - (i + 1)
        if not nxt or not nxt.isspace():
            continue

        if ch in ".!?":
            ultima = corrente.strip().split()[-1] if corrente.strip() else ""
            if re.fullmatch(r"\d+\.", ultima):
                continue
            if re.fullmatch(r"[A-Z][a-z]?\.", ultima):
                continue
            pezzi.append(corrente)
            corrente = ""
            continue

        if ch in ",;:" and len(corrente.strip()) >= minimo and resto >= look:
            pezzi.append(corrente)
            corrente = ""
            continue

        if len(corrente) >= MAX_SPEAK_CHARS:
            pezzi.append(corrente)
            corrente = ""
    return pezzi


# -- bersagli-----------------------------------------------------------

def _aperta(porta: int) -> bool:
    import socket
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def scegli_bersaglio(voce: str):
    """Restituisce (nome, funzione che costruisce la Request)."""
    if _aperta(7000):
        def req(testo):
            url = "http://127.0.0.1:7000/api/tts/stream?text=" + urllib.parse.quote(testo)
            return urllib.request.Request(url)
        return "Odysseus /api/tts/stream (catena intera)", req

    if _aperta(8013):
        def req(testo):
            corpo = json.dumps({"model": "pocket-tts", "input": testo,
                                "voice": voce, "response_format": "wav"}).encode()
            return urllib.request.Request("http://127.0.0.1:8013/v1/audio/speech", data=corpo,
                                          headers={"Content-Type": "application/json"})
        return "ponte voce /v1/audio/speech", req

    if _aperta(8014):
        def req(testo):
            return richiesta_pockettts(testo, voce)
        return "PocketTTS /tts (diretto)", req

    return None, None


def richiesta_pockettts(testo: str, voce: str) -> urllib.request.Request:
    """PocketTTS vuole multipart/form-data, non JSON: chi gli manda JSON si
    prende un 422 e crede che il servizio sia morto."""
    b = uuid.uuid4().hex
    corpo = b""
    for chiave, valore in (("text", testo), ("voice_url", voce)):
        if valore is None:
            continue
        corpo += (f'--{b}\r\nContent-Disposition: form-data; name="{chiave}"\r\n\r\n{valore}\r\n').encode()
    corpo += f"--{b}--\r\n".encode()
    return urllib.request.Request("http://127.0.0.1:8014/tts", data=corpo,
                                  headers={"Content-Type": "multipart/form-data; boundary=" + b})


# -- misura-------------------------------------------------------------

def sintetizza(costruisci, testo: str) -> dict:
    t0 = time.monotonic()
    primo = None
    n = 0
    try:
        with urllib.request.urlopen(costruisci(testo), timeout=300) as r:
            while True:
                p = r.read1(8192)
                if not p:
                    break
                if primo is None:
                    primo = time.monotonic() - t0
                n += len(p)
    except Exception as e:  # noqa: BLE001
        return {"errore": f"{type(e).__name__}: {e}", "t_inizio": t0}
    return {"t_inizio": t0, "primo_byte": primo or 0.0,
            "totale": time.monotonic() - t0, "byte": n,
            # WAV 16 bit mono 24 kHz, meno le 44 byte di intestazione
            "durata": max(0.0, (n - 44) / 2 / 24000)}


def ram_del_servizio() -> str:
    ps = ("$p=(Get-NetTCPConnection -LocalPort 8014 -State Listen -ErrorAction SilentlyContinue).OwningProcess;"
          "if($p){[int]((Get-Process -Id $p).WorkingSet64/1MB)}else{0}")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return f"{out} MB (working set del processo in ascolto sulla 8014)"
    except Exception:  # noqa: BLE001
        return "non misurabile"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tok-s", type=float, default=70.0, help="velocita' del finto modello")
    ap.add_argument("--voce", default="giovanni", help="voce PocketTTS (ignorata su Odysseus)")
    args = ap.parse_args()

    nome, costruisci = scegli_bersaglio(args.voce)
    if costruisci is None:
        print("Nessun pezzo della catena vocale e' acceso (7000/8013/8014). "
              "Avvia almeno PocketTTS e riprova.")
        return 1
    print(f"bersaglio: {nome}\nvoce: {args.voce}   modello finto: {args.tok_s:.0f} token/s\n")

    # La sintesi gira in parallelo al testo, come nel browser: un lavoratore
    # solo, in fila, che parte appena c'e' qualcosa da dire. Misurare a testo
    # finito darebbe numeri finti (ogni richiesta partirebbe in ritardo).
    import queue as _queue
    import threading
    coda_lavoro: _queue.Queue = _queue.Queue()
    risultati: list = []

    def lavoratore():
        while True:
            voce_da_dire = coda_lavoro.get()
            if voce_da_dire is None:
                return
            t_pronto, testo = voce_da_dire
            r = sintetizza(costruisci, testo)
            r["t_pronto"] = t_pronto
            r["testo"] = testo
            risultati.append(r)

    filo = threading.Thread(target=lavoratore, daemon=True)
    filo.start()

    # Il finto modello: ~4 caratteri per token.
    passo = 4.0 / args.tok_s
    t_avvio = time.monotonic()

    n_pezzi = 0
    accumulato = ""
    inviati = 0          # caratteri gia' consumati, come _streamSentencesSent
    pendente = ""
    ultimo_debounce = -1.0
    t_primo_token = None

    time.sleep(RAGIONAMENTO_S)   # fase "thinking": il browser non parla ancora

    def emetti(testo: str, con_pausa: bool):
        nonlocal accumulato, inviati, pendente, ultimo_debounce, t_primo_token, n_pezzi
        for i in range(0, len(testo), 4):
            accumulato += testo[i:i + 4]
            if t_primo_token is None:
                t_primo_token = time.monotonic()
            time.sleep(passo)
            ora = time.monotonic()
            # stessa finestra di attesa del browser: un aggiornamento ogni 150 ms
            if ora - ultimo_debounce < DEBOUNCE_S:
                continue
            ultimo_debounce = ora
            regione = accumulato[inviati:]
            primo_del_turno = inviati == 0
            for pezzo in spezza(regione, primo_del_turno):
                pendente += pezzo
                inviati += len(pezzo)
                soglia = MIN_FIRST_SPEAK_CHARS if primo_del_turno else MIN_SPEAK_CHARS
                if len(pendente.strip()) < soglia:
                    continue
                coda_lavoro.put((time.monotonic(), pendente.strip()))
                n_pezzi += 1
                pendente = ""
        if con_pausa:
            time.sleep(PAUSA_STRUMENTO_S)

    emetti(RISPOSTA, con_pausa=True)
    emetti(RISPOSTA_2, con_pausa=False)
    # coda di fine turno (streamingEnd): quello che resta si dice comunque
    coda = (pendente + accumulato[inviati:]).strip()
    if coda:
        coda_lavoro.put((time.monotonic(), coda))
        n_pezzi += 1
    t_fine_testo = time.monotonic()

    coda_lavoro.put(None)
    filo.join(timeout=900)

    print(f"{n_pezzi} pezzi da dire. Il testo intero ci mette "
          f"{t_fine_testo - t_avvio:.1f} s ad arrivare.\n")
    print(f"{'#':>2} {'pronto':>8} {'attesa':>7} {'1o byte':>8} {'totale':>7} {'audio':>7}  testo")
    for i, r in enumerate(risultati, 1):
        if "errore" in r:
            print(f"{i:>2} {r['t_pronto'] - t_avvio:7.2f}s  ERRORE: {r['errore']}")
            continue
        print(f"{i:>2} {r['t_pronto'] - t_avvio:7.2f}s {r['t_inizio'] - r['t_pronto']:6.2f}s "
              f"{r['primo_byte']:7.2f}s {r['totale']:6.2f}s {r['durata']:6.2f}s  {r['testo'][:46]}...")

    buoni = [r for r in risultati if "errore" not in r]
    if not buoni:
        print("\nnessun pezzo sintetizzato: catena rotta.")
        return 1

    # -- bilancio dei tempi----------------------------------------------
    primo = buoni[0]
    # riproduzione in serie: il pezzo n parte quando finisce il n-1
    orologio = primo["t_inizio"] + primo["primo_byte"]
    t_primo_suono = orologio
    fame = 0.0
    for r in buoni:
        disponibile = r["t_inizio"] + r["primo_byte"]
        if disponibile > orologio:
            fame += disponibile - orologio
            orologio = disponibile
        orologio += r["durata"]

    somma_audio = sum(r["durata"] for r in buoni)
    somma_calcolo = sum(r["totale"] for r in buoni)

    print("\n-- bilancio --")
    print(f"  primo token del modello        +{t_primo_token - t_avvio:5.2f} s")
    print(f"  primo pezzo tagliabile         +{buoni[0]['t_pronto'] - t_avvio:5.2f} s")
    print(f"  richiesta partita              +{buoni[0]['t_inizio'] - t_avvio:5.2f} s")
    print(f"  PRIMO SUONO                    +{t_primo_suono - t_avvio:5.2f} s"
          f"   (ritardo dal primo token: {t_primo_suono - t_primo_token:.2f} s)")
    print(f"  testo finito                   +{t_fine_testo - t_avvio:5.2f} s")
    print(f"  voce finita                    +{orologio - t_avvio:5.2f} s"
          f"   (coda dopo il testo: {orologio - t_fine_testo:.1f} s)")
    print(f"  audio prodotto {somma_audio:.1f} s in {somma_calcolo:.1f} s di calcolo "
          f"-> fattore tempo reale {somma_calcolo / somma_audio:.2f}")
    print(f"  silenzi per sintesi in ritardo: {fame:.2f} s")
    print(f"  RAM: {ram_del_servizio()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
