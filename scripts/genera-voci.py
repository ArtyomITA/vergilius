import time
import soundfile as sf
from kokoro_onnx import Kokoro

TESTO = ("Ciao! Sono la voce del tuo assistente personale. "
         "Posso aiutarti mentre giochi, cercare informazioni sul web "
         "e controllare il tuo computer. Dimmi pure cosa ti serve.")

kokoro = Kokoro(r"d:\assistenteeee\tts-models\kokoro-v1.0.onnx",
                r"d:\assistenteeee\tts-models\voices-v1.0.bin")

for voce in ["if_sara", "im_nicola"]:
    t0 = time.time()
    campioni, sr = kokoro.create(TESTO, voice=voce, speed=1.0, lang="it")
    dt = time.time() - t0
    out = rf"d:\assistenteeee\voice-samples\kokoro-{voce}.wav"
    sf.write(out, campioni, sr)
    durata = len(campioni) / sr
    print(f"{voce}: {durata:.1f}s audio in {dt:.1f}s sintesi (RTF {dt/durata:.2f})")
