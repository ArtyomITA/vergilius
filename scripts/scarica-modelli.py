r"""Vergilius — scarica i modelli locali (primo avvio).

Vergilius funziona con modelli GGUF che stanno sul tuo disco: non sono nel
repository (pesano gigabyte) e non vengono mai caricati altrove. Questo script
li prende da Hugging Face e li mette dove il programma li cerca.

    python scripts/scarica-modelli.py                 il necessario (~4,2 GB)
    python scripts/scarica-modelli.py --con-ling      aggiunge Ling-3.0-tiny, il cervello alternativo
    python scripts/scarica-modelli.py --con-heretic   aggiunge il modello senza filtri (QwenPaw 9B)
    python scripts/scarica-modelli.py --con-lfm-uncensored   aggiunge LFM2.5-2.6B senza filtri
    python scripts/scarica-modelli.py --elenco        mostra cosa serve e cosa c'è già

Cosa scarica, e perché:

  lfm       LFM2.5-2.6B Q8_0 (2,9 GB) + drafter DSpark Q8_0 (0,4 GB) — il cervello.
            Modello denso ibrido di Liquid AI: sceglie bene gli strumenti, non
            inventa i dati, e su una scheda vecchia legge il prompt a ~1900 token
            al secondo. Il drafter accelera la scrittura del 25-70%.
            Licenza LFM Open License v1.0 (base Apache 2.0): uso commerciale libero
            sotto i 10 milioni di dollari di ricavi annui. Scaricandolo ne accetti
            i termini: https://huggingface.co/LiquidAI/LFM2.5-2.6B

  occhi     Holo-3.1-0.8B Q6_K + proiettore (0,9 GB) — la vista. Gira sulla CPU,
            così non toglie memoria video al cervello. Serve a leggere lo schermo
            e le immagini.

  ling      Ling-3.0-tiny Q6_K (6,4 GB) — facoltativo. Il cervello precedente,
            MoE da 7,9 miliardi di parametri (1,3 attivi). Resta selezionabile.

  lfm-uncensored   LFM2.5-2.6B senza rifiuti (2,9 GB) — facoltativo, lo scegli tu.
            Stessa base del cervello predefinito, MODIFICATA DA TERZI (SC117, abliterazione):
            non e' un rilascio di Liquid AI e nessuno l'ha revisionato. Togliere i rifiuti
            puo' togliere anche la prudenza nel dire «non lo so». Licenza LFM Open License
            v1.0, come la base: https://huggingface.co/SC117/LFM2.5-2.6B-Uncensored-GGUF

  heretic   QwenPaw-Flash-9B senza filtri (5,2 GB) — facoltativo, lo scegli tu.
            Modello alternativo per compiti in cui i rifiuti automatici danno
            fastidio. Vergilius funziona benissimo senza.

Ha bisogno di `huggingface_hub` (pip install huggingface_hub) oppure, se c'è,
usa aria2c per scaricare più veloce. Riprende un download interrotto.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
MODELLI = RADICE / "models"
VLM = MODELLI / "vlm"

# (chiave, repo Hugging Face, file nel repo, cartella locale, GB, a cosa serve)
CATALOGO = [
    ("lfm", "LiquidAI/LFM2.5-2.6B-GGUF", "LFM2.5-2.6B-Q8_0.gguf",
     MODELLI, "LFM2.5-2.6B-Q8_0.gguf", 2.9, "il cervello: chat, strumenti, ragionamento"),
    ("lfm", "LiquidAI/LFM2.5-2.6B-DSpark-GGUF", "LFM2.5-2.6B-DSpark-Q8_0.gguf",
     MODELLI, "LFM2.5-2.6B-DSpark-Q8_0.gguf", 0.4, "drafter speculativo, va con LFM"),
    ("occhi", "mradermacher/Holo-3.1-0.8B-GGUF", "Holo-3.1-0.8B.Q6_K.gguf",
     VLM, "Holo-3.1-0.8B.Q6_K.gguf", 0.7, "la vista: legge schermo e immagini (CPU)"),
    ("occhi", "mradermacher/Holo-3.1-0.8B-GGUF", "Holo-3.1-0.8B.mmproj-f16.gguf",
     VLM, "Holo-3.1-0.8B.mmproj-f16.gguf", 0.2, "proiettore visivo, va con Holo"),
    ("ling", "bartowski/inclusionAI_Ling-3.0-tiny-GGUF", "inclusionAI_Ling-3.0-tiny-Q6_K.gguf",
     MODELLI, "Ling-3.0-tiny-Q6_K.gguf", 6.4, "cervello alternativo (facoltativo)"),
    ("lfm-uncensored", "SC117/LFM2.5-2.6B-Uncensored-GGUF", "LFM2.5-2.6B-Uncensored-Q8_0.gguf",
     MODELLI, "LFM2.5-2.6B-Uncensored-Q8_0.gguf", 2.9, "LFM senza rifiuti, modificato da terzi (facoltativo)"),
    ("heretic", "mradermacher/QwenPaw-Flash-9B-heretic-i1-GGUF", "QwenPaw-Flash-9B-heretic.i1-Q4_K_M.gguf",
     MODELLI, "QwenPaw-Flash-9B-heretic-Q4_K_M.gguf", 5.2, "alternativa senza filtri (facoltativo)"),
]

FACOLTATIVI = {"ling", "heretic", "lfm-uncensored"}


def presenti() -> dict:
    return {v[4]: (v[3] / v[4]) for v in CATALOGO if (v[3] / v[4]).exists()}


def elenco() -> None:
    ci_sono = presenti()
    print(f"cartella modelli: {MODELLI}\n")
    gruppo = None
    for chiave, repo, remoto, cartella, locale, gb, perche in CATALOGO:
        if chiave != gruppo:
            print(f"  [{chiave}]")
            gruppo = chiave
        stato = "già presente" if locale in ci_sono else f"da scaricare, {gb:.1f} GB"
        print(f"    {locale:44} {stato}")
        print(f"      {perche}")
    manca = sum(v[5] for v in CATALOGO if v[0] not in FACOLTATIVI and v[4] not in ci_sono)
    if manca:
        print(f"\n  totale da scaricare (senza i facoltativi): {manca:.1f} GB")
    else:
        print("\n  tutto il necessario è già sul disco.")


def _scarica_aria(url: str, destinazione: Path) -> bool:
    aria = shutil.which("aria2c")
    if not aria:
        return False
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    print(f"  aria2c, 8 connessioni -> {destinazione.name}")
    r = subprocess.run([aria, "-x", "8", "-s", "8", "-k", "4M", "--continue=true",
                        "--summary-interval=15", "--console-log-level=warn",
                        "-d", str(destinazione.parent), "-o", destinazione.name, url])
    return r.returncode == 0 and destinazione.exists()


def _scarica_hf(repo: str, remoto: str, destinazione: Path) -> bool:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("  serve `pip install huggingface_hub` (oppure installa aria2c)")
        return False
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    print(f"  huggingface_hub -> {destinazione.name}")
    percorso = hf_hub_download(repo_id=repo, filename=remoto, local_dir=str(destinazione.parent))
    scaricato = Path(percorso)
    if scaricato.resolve() != destinazione.resolve():
        scaricato.replace(destinazione)
    return destinazione.exists()


def scarica(con_heretic: bool, con_ling: bool = False, con_lfm_uncensored: bool = False) -> int:
    ci_sono = presenti()
    da_fare = [v for v in CATALOGO
               if v[4] not in ci_sono and (con_heretic or v[0] != "heretic")
               and (con_ling or v[0] != "ling")
               and (con_lfm_uncensored or v[0] != "lfm-uncensored")]
    if not da_fare:
        print("Tutto già presente, niente da scaricare.")
        return 0
    totale = sum(v[5] for v in da_fare)
    print(f"Da scaricare: {len(da_fare)} file, circa {totale:.1f} GB\n")
    falliti = []
    for chiave, repo, remoto, cartella, locale, gb, perche in da_fare:
        destinazione = cartella / locale
        url = f"https://huggingface.co/{repo}/resolve/main/{remoto}?download=true"
        print(f"[{chiave}] {locale} ({gb:.1f} GB) — {perche}")
        ok = _scarica_aria(url, destinazione) or _scarica_hf(repo, remoto, destinazione)
        if ok:
            mb = destinazione.stat().st_size / 1048576
            print(f"  fatto: {mb:,.0f} MB\n".replace(",", "."))
        else:
            falliti.append(locale)
            print("  NON riuscito\n")
    if falliti:
        print("Non scaricati: " + ", ".join(falliti))
        print("Riprova: il download riparte da dove si era fermato.")
        return 1
    print("Modelli pronti. Avvia Vergilius con AVVIA-VERGILIUS.bat")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Scarica i modelli locali di Vergilius")
    p.add_argument("--con-heretic", action="store_true",
                   help="scarica anche il modello alternativo senza filtri (5,2 GB)")
    p.add_argument("--con-ling", action="store_true",
                   help="scarica anche Ling-3.0-tiny, il cervello alternativo (6,4 GB)")
    p.add_argument("--con-lfm-uncensored", action="store_true",
                   help="scarica anche LFM2.5-2.6B senza rifiuti, modificato da terzi (2,9 GB)")
    p.add_argument("--elenco", action="store_true", help="mostra cosa serve e cosa c'è già")
    a = p.parse_args()
    if a.elenco:
        elenco()
        return 0
    return scarica(a.con_heretic, a.con_ling, a.con_lfm_uncensored)


if __name__ == "__main__":
    sys.exit(main())
