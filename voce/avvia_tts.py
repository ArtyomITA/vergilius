r"""Avvia PocketTTS come fa `pocket-tts serve`, ma con piu' di un filo di calcolo.

Il pacchetto fissa `torch.set_num_threads(1)` dentro
`pocket_tts/models/tts_model.py` (riga 49), che viene eseguita all'import. Su
otto core ne usa uno solo. Qui si importa il pacchetto (quindi la riga scatta),
si rimette il numero di fili PRIMA che il modello venga caricato, e poi si
chiama la stessa funzione `serve` con gli stessi argomenti: nessuna modifica a
site-packages, che verrebbe cancellata al primo aggiornamento del pacchetto.

Tetto a 4 fili per scelta, non per limite di torch: il modello sulla GPU e'
legato al lancio dei kernel e vuole un core libero a girare. Se la sintesi si
prende tutti e otto i core, la voce arriva prima ma il modello rallenta.

Uso (identico a quello del comando originale):
    python voce\avvia_tts.py --language italian --quantize --host 127.0.0.1 --port 8014
    VERGILIUS_TTS_THREADS=2   per cambiare il numero di fili
"""

import argparse
import os
import sys

# Valore predefinito: misurato sul banco (vedi ricerche), oltre non si guadagna.
FILI_PREDEFINITI = 2
FILI_MASSIMI = 4


def fili_richiesti() -> int:
    """Numero di fili da dare a torch, sempre fra 1 e FILI_MASSIMI."""
    grezzo = os.getenv("VERGILIUS_TTS_THREADS", str(FILI_PREDEFINITI))
    try:
        n = int(grezzo)
    except (TypeError, ValueError):
        n = FILI_PREDEFINITI
    return max(1, min(FILI_MASSIMI, n))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PocketTTS con fili configurabili")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--language", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--quantize", action="store_true")
    ap.add_argument("--reload", action="store_true")
    argomenti = list(sys.argv[1:] if argv is None else argv)
    # Tolleranza: chi copia la riga vecchia scrive ancora "serve" come primo
    # argomento. Qui il sottocomando e' uno solo, quindi si ignora.
    if argomenti and argomenti[0] == "serve":
        argomenti.pop(0)
    args = ap.parse_args(argomenti)

    # L'import fa scattare il set_num_threads(1) del pacchetto: si rimette dopo.
    from pocket_tts import main as pocket_main
    import torch

    n = fili_richiesti()
    torch.set_num_threads(n)
    try:
        # Puo' essere gia' stato fissato da un'altra parte: non e' un errore.
        torch.set_num_interop_threads(min(2, n))
    except RuntimeError:
        pass
    print(f"[avvia_tts] fili torch: {torch.get_num_threads()}", flush=True)

    pocket_main.serve(
        host=args.host,
        port=args.port,
        reload=args.reload,
        language=args.language,
        config=args.config,
        quantize=args.quantize,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
