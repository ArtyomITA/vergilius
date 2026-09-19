"""La fine turno automatica di sherpa-onnx basta, o serve Silero VAD a parte?

sherpa-onnx ha `enable_endpoint_detection` con tre regole:
  regola 1  silenzio dopo che NON e' stato decodificato nulla
  regola 2  silenzio dopo che qualcosa E' stato decodificato   <- questa e' la nostra
  regola 3  lunghezza massima dell'enunciato

Se `is_endpoint()` scatta al momento giusto, il rilevatore di voce separato nel
browser diventa superfluo per la fine turno: l'ASR gia' sa quando hai finito.

Prova: parlato + silenzio in coda, si guarda quanto tardi scatta.
"""

import io
import sys
import time
import wave

import numpy as np
import sherpa_onnx

MODELLO = ("d:/assistenteeee/asr-models/"
           "sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-320ms-int8-2026-06-11")
FILE = "d:/assistenteeee/voice-samples/campione_nuovo_16k.wav"
PEZZO_MS = 100
SILENZIO_CODA_S = 2.5


def leggi(percorso):
    with wave.open(percorso, "rb") as w:
        sr = w.getframerate()
        dati = w.readframes(w.getnframes())
    return np.frombuffer(dati, dtype=np.int16).astype(np.float32) / 32768.0, sr


def main():
    campioni, sr = leggi(FILE)
    # Solo i primi 8 secondi, poi silenzio: interessa quando scatta, non cosa dice.
    campioni = campioni[: sr * 8]
    silenzio = np.zeros(int(sr * SILENZIO_CODA_S), dtype=np.float32)
    tutto = np.concatenate([campioni, silenzio])
    fine_parlato = len(campioni) / sr

    for soglia in (0.5, 0.8, 1.2):
        rec = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=f"{MODELLO}/tokens.txt",
            encoder=f"{MODELLO}/encoder.int8.onnx",
            decoder=f"{MODELLO}/decoder.int8.onnx",
            joiner=f"{MODELLO}/joiner.int8.onnx",
            num_threads=2,
            provider="cpu",
            model_type="nemo_transducer",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=soglia,
            rule3_min_utterance_length=300.0,
        )
        stream = rec.create_stream()
        try:
            stream.set_option("language", "it")
        except Exception:
            pass

        passo = int(sr * PEZZO_MS / 1000)
        scatto = None
        testo_allo_scatto = ""

        for i in range(0, len(tutto), passo):
            pezzo = tutto[i:i + passo]
            istante = (i + len(pezzo)) / sr
            stream.accept_waveform(sr, pezzo)
            while rec.is_ready(stream):
                rec.decode_stream(stream)
            if scatto is None and rec.is_endpoint(stream):
                scatto = istante
                testo_allo_scatto = rec.get_result(stream)
                break

        if scatto is None:
            print(f"regola2 = {soglia}s   NON e' scattato in "
                  f"{SILENZIO_CODA_S}s di silenzio")
        else:
            print(f"regola2 = {soglia}s   scattato a {scatto:.2f}s "
                  f"({(scatto-fine_parlato)*1000:.0f} ms dopo la fine del parlato)")
            print(f"              testo: {testo_allo_scatto[-60:]!r}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
