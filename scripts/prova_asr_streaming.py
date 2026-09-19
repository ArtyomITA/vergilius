"""Nemotron-3.5 ASR streaming su CPU: funziona in italiano? quanto costa?

Simula il microfono: spinge l'audio a pezzi da 100 ms come farebbe un browser,
e stampa il testo parziale man mano che esce. Quello che si misura non e' la
velocita' totale (interessa poco) ma **quanto tardi arriva il primo testo** e
quanto il riconoscitore resta indietro rispetto al parlato.

Uso:  python prova_asr_streaming.py [file.wav] [lingua]
"""

import sys
import time
import wave

import numpy as np
import sherpa_onnx

MODELLO = ("d:/assistenteeee/asr-models/"
           "sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-320ms-int8-2026-06-11")
FILE = sys.argv[1] if len(sys.argv) > 1 else "d:/assistenteeee/voice-samples/campione_nuovo_16k.wav"
LINGUA = sys.argv[2] if len(sys.argv) > 2 else "it"
PEZZO_MS = 100


def leggi_wav(percorso):
    with wave.open(percorso, "rb") as w:
        assert w.getnchannels() == 1, "serve mono"
        assert w.getsampwidth() == 2, "servono campioni a 16 bit"
        sr = w.getframerate()
        dati = w.readframes(w.getnframes())
    campioni = np.frombuffer(dati, dtype=np.int16).astype(np.float32) / 32768.0
    return campioni, sr


def costruisci(threads):
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=f"{MODELLO}/tokens.txt",
        encoder=f"{MODELLO}/encoder.int8.onnx",
        decoder=f"{MODELLO}/decoder.int8.onnx",
        joiner=f"{MODELLO}/joiner.int8.onnx",
        num_threads=threads,
        provider="cpu",
        model_type="nemo_transducer",
        # Fine turno automatica: e' il sostituto naturale del click a mano.
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=2.4,
        rule2_min_trailing_silence=0.8,
        rule3_min_utterance_length=20.0,
    )


def main():
    campioni, sr = leggi_wav(FILE)
    durata = len(campioni) / sr
    print(f"file    : {FILE}")
    print(f"durata  : {durata:.1f}s a {sr} Hz")
    print(f"lingua  : {LINGUA}")
    print(f"modello : 320ms, int8\n")

    for threads in (2, 4):
        print(f"=== {threads} thread ===")
        t0 = time.time()
        rec = costruisci(threads)
        print(f"  caricamento           {time.time()-t0:6.2f}s")

        stream = rec.create_stream()
        # La lingua si passa per flusso, non per modello: il 3.5 e' multilingua
        # con riconoscimento automatico, ma dichiararla aiuta la precisione.
        try:
            stream.set_option("language", LINGUA)
            lingua_ok = True
        except Exception as e:
            lingua_ok = False
            print(f"  set_option(language) non accettato: {e}")

        passo = int(sr * PEZZO_MS / 1000)
        primo_testo = None
        ultimo = ""
        ritardi = []
        parziali = 0
        t_inizio = time.time()

        for i in range(0, len(campioni), passo):
            pezzo = campioni[i:i + passo]
            istante_audio = (i + len(pezzo)) / sr

            t_pezzo = time.time()
            stream.accept_waveform(sr, pezzo)
            while rec.is_ready(stream):
                rec.decode_stream(stream)
            ritardi.append(time.time() - t_pezzo)

            testo = rec.get_result(stream)
            if testo != ultimo:
                parziali += 1
                if primo_testo is None:
                    primo_testo = (time.time() - t_inizio, istante_audio, testo)
                ultimo = testo

        stream.input_finished()
        while rec.is_ready(stream):
            rec.decode_stream(stream)
        finale = rec.get_result(stream)

        totale = time.time() - t_inizio
        ritardi_ms = np.array(ritardi) * 1000

        if primo_testo:
            t_orologio, t_audio, txt = primo_testo
            print(f"  primo testo dopo      {t_orologio:6.2f}s di orologio, "
                  f"{t_audio:.2f}s di audio -> {txt[:40]!r}")
        else:
            print("  NESSUN testo prodotto")
        print(f"  aggiornamenti         {parziali}")
        print(f"  per pezzo da {PEZZO_MS}ms   "
              f"medio {ritardi_ms.mean():.1f}ms  "
              f"p95 {np.percentile(ritardi_ms,95):.1f}ms  "
              f"max {ritardi_ms.max():.1f}ms")
        print(f"  RTF                   {totale/durata:.3f}   "
              f"({'in tempo reale' if totale < durata else 'TROPPO LENTO'})")
        print(f"  lingua dichiarata     {'si' if lingua_ok else 'no (automatica)'}")
        print(f"  testo finale:\n    {finale}\n")


if __name__ == "__main__":
    main()
