"""Quanto passa dalla richiesta al PRIMO byte di audio?

E' l'unico numero che conta per la voce: non quanto ci mette a finire, ma
quanto ci mette a cominciare. Misura tre punti della catena, cosi' si vede
dove il ritardo nasce e dove veniva aggiunto.

  1. PocketTTS diretto            :8014/tts
  2. ponte voce                   :8013/v1/audio/speech
  3. Odysseus                     :7000/api/tts/stream   (se in piedi)

Per ognuno: tempo al primo byte, tempo all'ultimo, e quanti secondi di audio
sono usciti (l'intestazione WAV dice 24 kHz, 16 bit, mono).

Uso:  python misura_voce_primo_suono.py
"""

import sys
import time
import urllib.parse
import urllib.request

FRASI = [
    "Ciao, sono pronto.",
    "Ci sono tre allerte importanti in Ucraina in questo momento.",
    "Nella zona di Kiev risultano quattro voli militari e due allerte aeree, "
    "mentre a sud la situazione resta piu' calma rispetto a ieri.",
]

WAV_INTESTAZIONE = 44
BYTE_PER_SECONDO = 24000 * 2  # 24 kHz, 16 bit, mono


def misura(nome, costruisci_richiesta):
    print(f"\n=== {nome} ===")
    for frase in FRASI:
        try:
            req = costruisci_richiesta(frase)
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=180) as r:
                primo = None
                totale = 0
                while True:
                    pezzo = r.read(4096)
                    if not pezzo:
                        break
                    if primo is None:
                        primo = time.time() - t0
                    totale += len(pezzo)
                fine = time.time() - t0
        except Exception as e:
            print(f"  {len(frase):>3} car  ERRORE: {type(e).__name__}: {e}")
            continue

        audio_s = max(0, totale - WAV_INTESTAZIONE) / BYTE_PER_SECONDO
        vantaggio = fine - (primo or fine)
        print(f"  {len(frase):>3} car  primo byte {primo:6.2f}s   "
              f"ultimo {fine:6.2f}s   audio {audio_s:5.2f}s   "
              f"anticipo {vantaggio:5.2f}s")


def pockettts(frase):
    dati = urllib.parse.urlencode({"text": frase, "voice_url": "estelle"}).encode()
    return urllib.request.Request("http://127.0.0.1:8014/tts", data=dati)


def ponte(frase):
    import json
    corpo = json.dumps({"model": "pocket-tts", "input": frase,
                        "voice": "estelle", "response_format": "wav"}).encode()
    return urllib.request.Request("http://127.0.0.1:8013/v1/audio/speech",
                                  data=corpo,
                                  headers={"Content-Type": "application/json"})


def odysseus(frase):
    url = "http://127.0.0.1:7000/api/tts/stream?text=" + urllib.parse.quote(frase)
    return urllib.request.Request(url)


def main():
    print("'anticipo' = quanto audio si sarebbe potuto gia' ascoltare mentre")
    print("il resto arrivava. Con i buffer di prima era sempre 0.")
    misura("1. PocketTTS diretto", pockettts)
    misura("2. ponte voce :8013", ponte)
    misura("3. Odysseus :7000", odysseus)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
