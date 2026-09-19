r"""Genera un corpus REALE di risposte del modello per misurare il rilevatore di
"annuncio senza azione" (`_INTENT_RE` in agent_loop.py).

Perche' serve: il 26 ago il modello ha scritto "eseguo ora una ricerca sui mercati" senza
chiamare nulla, e il rilevatore non l'ha agganciato. Ampliare la lista dei verbi a mano e'
gia' fallito due volte (lo dice il commento nel codice). Per fare meglio serve un corpus di
frasi VERE prodotte da QUESTO modello, non frasi immaginate da noi.

Cosa fa: manda decine di domande che coprono i domini dei nostri 71 strumenti, registra la
risposta e se una chiamata e' avvenuta. Le risposte SENZA chiamata sono il materiale su cui
misurare quanti annunci il rilevatore prende e quanti ne perde.

Uso:
  odysseus\venv\Scripts\python.exe scripts\corpus-annunci.py --ripetizioni 2

Esito: ricerche/toolcall/corpus-<data>.json  (poi: scripts/valuta-annunci.py)
Non tocca la produzione: parla con llama-swap come farebbe Odysseus.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(r"d:\assistenteeee")
URL = "http://127.0.0.1:8012/v1/chat/completions"
USCITE = WORKSPACE / "ricerche" / "toolcall"


def _regole_vere() -> str:
    try:
        src = (WORKSPACE / "odysseus" / "src" / "agent_loop.py").read_text(encoding="utf-8")
        m = re.search(
            "_API_AGENT_RULES" + r"\s*=\s*" + '(?:r?"""|' + r"r?''')" + "(.*?)" + '(?:"""|' + r"''')",
            src, re.S)
        return m.group(1) if m else ""
    except Exception:
        return ""


def _f(nome: str, descr: str, prop: dict, req: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": nome, "description": descr,
        "parameters": {"type": "object", "properties": prop, "required": req}}}


T = {"type": "string"}
# Un campione trasversale dei domini coperti dai nostri 71 strumenti.
STRUMENTI = [
    _f("web_search", "Ricerca web per un fatto puntuale.", {"query": T}, ["query"]),
    _f("web_fetch", "Scarica il contenuto di una pagina.", {"url": T}, ["url"]),
    _f("fin_mercati", "Prezzi e dati di mercato in tempo reale.", {"simbolo": T}, ["simbolo"]),
    _f("fin_notizie", "Notizie finanziarie recenti.", {"tema": T}, ["tema"]),
    _f("osint_notizie", "Notizie di attualita' e geopolitica.", {"tema": T}, ["tema"]),
    _f("osint_web", "Ricerca sul web aperto per OSINT.", {"query": T}, ["query"]),
    _f("read_file", "Legge un file dal disco.", {"percorso": T}, ["percorso"]),
    _f("write_file", "Scrive un file su disco.", {"percorso": T, "contenuto": T}, ["percorso", "contenuto"]),
    _f("edit_file", "Modifica un file esistente.", {"percorso": T, "modifica": T}, ["percorso", "modifica"]),
    _f("grep", "Cerca un testo nei file.", {"pattern": T}, ["pattern"]),
    _f("ls", "Elenca i file di una cartella.", {"percorso": T}, ["percorso"]),
    _f("bash", "Esegue un comando di shell.", {"comando": T}, ["comando"]),
    _f("python", "Esegue codice Python.", {"codice": T}, ["codice"]),
    _f("list_emails", "Elenca le email in arrivo.", {"cartella": T}, ["cartella"]),
    _f("send_email", "Invia una email.", {"a": T, "oggetto": T, "corpo": T}, ["a", "oggetto", "corpo"]),
    _f("manage_calendar", "Crea o modifica eventi di calendario.", {"azione": T}, ["azione"]),
    _f("manage_memory", "Salva o rilegge memorie dell'utente.", {"azione": T}, ["azione"]),
    _f("manage_tasks", "Gestisce le attivita' da fare.", {"azione": T}, ["azione"]),
    _f("manage_notes", "Gestisce le note.", {"azione": T}, ["azione"]),
    _f("create_document", "Crea un documento.", {"titolo": T, "contenuto": T}, ["titolo", "contenuto"]),
    _f("trigger_research", "Avvia una ricerca approfondita.", {"tema": T}, ["tema"]),
    _f("list_models", "Elenca i modelli disponibili.", {"filtro": T}, ["filtro"]),
    _f("ask_user", "Chiede un chiarimento all'utente.", {"domanda": T}, ["domanda"]),
    _f("update_plan", "Aggiorna il piano di lavoro.", {"passi": T}, ["passi"]),
]

# Domande che DEVONO produrre una chiamata. Coprono tutti i domini, con formulazioni
# diverse (dirette, indirette, colloquiali) perche' la formulazione cambia la risposta.
DOMANDE = [
    ("web", "Chi ha vinto l'ultima gara di Formula 1?"),
    ("web", "Che tempo fa a Milano adesso?"),
    ("web", "Cerca cosa e' successo oggi in Medio Oriente."),
    ("web", "Mi sai dire l'ultima versione stabile di Python?"),
    ("fin", "Quanto vale Apple in questo momento?"),
    ("fin", "Com'e' messo bitcoin oggi?"),
    ("fin", "A livello financial che novita' abbiamo?"),
    ("fin", "Dammi un quadro dei mercati di stamattina."),
    ("fin", "Ci sono notizie su Nvidia?"),
    ("osint", "Che e' successo nel mondo nelle ultime due ore?"),
    ("osint", "Situazione nello stretto di Hormuz adesso?"),
    ("osint", "Aggiornami sulla situazione in Ucraina."),
    ("file", "Leggi il file config.yaml e dimmi cosa contiene."),
    ("file", "Quanti file .py ci sono nella cartella src?"),
    ("file", "Cerca la parola TODO nei sorgenti."),
    ("file", "Crea un file note.txt con dentro la lista della spesa."),
    ("shell", "Quanto spazio libero c'e' sul disco?"),
    ("shell", "Fammi vedere i processi che consumano piu' memoria."),
    ("shell", "Calcolami la radice quadrata di 20449 con python."),
    ("email", "Ho email non lette?"),
    ("email", "Manda una mail a mario@esempio.it per dirgli che arrivo tardi."),
    ("agenda", "Che impegni ho domani?"),
    ("agenda", "Segnami una riunione giovedi' alle 15."),
    ("memoria", "Ricordati che preferisco le risposte brevi."),
    ("memoria", "Che cosa sai delle mie preferenze?"),
    ("compiti", "Aggiungi alla lista: comprare il latte."),
    ("note", "Prendi nota che devo chiamare il commercialista."),
    ("documenti", "Scrivimi un documento di due paragrafi sul fotovoltaico."),
    ("ricerca", "Fai una ricerca approfondita sulle batterie allo stato solido."),
    ("modelli", "Che modelli ho disponibili in locale?"),
    # Domande che NON devono produrre una chiamata: servono a misurare i falsi positivi.
    ("nessuna", "Come ti chiami?"),
    ("nessuna", "Spiegami in due righe cos'e' una cache LRU."),
    ("nessuna", "Quanto fa 17 per 23?"),
    ("nessuna", "Scrivimi una filastrocca di quattro versi sul mare."),
    ("nessuna", "Qual e' la differenza fra TCP e UDP?"),
    ("nessuna", "Traduci in inglese: il gatto dorme sul divano."),
]

BLOCCO_EMOZIONI_INIZIO = """<!-- avatar-emotions -->
Hai un volto animato che mostra le tue emozioni. Inserisci UN tag emozione
all'inizio di ogni risposta. Tag disponibili: [neutral] [fear] [sadness] [anger]
[disgust] [joy] [smirk] [surprise]. Scrivi il tag esattamente cosi', fra parentesi
quadre, senza spiegarlo mai all'utente. Usa [neutral] quando non c'e' una emozione
particolare."""

BLOCCO_EMOZIONI_FINE = """<!-- avatar-emotions -->
Hai un volto animato che mostra le tue emozioni. Chiudi ogni risposta con UN tag
emozione sull'ultima riga, da solo. Tag disponibili: [neutral] [fear] [sadness]
[anger] [disgust] [joy] [smirk] [surprise]. Scrivi il tag esattamente cosi', fra
parentesi quadre, senza spiegarlo mai all'utente. Usa [neutral] quando non c'e' una
emozione particolare."""

PERSONA = "assistente di adrian chiamata mao"


def costruisci_sistema(variante: str, regole: str) -> str:
    if variante == "tag-inizio":
        return f"{regole}\n\n{PERSONA}\n\n{BLOCCO_EMOZIONI_INIZIO}"
    if variante == "tag-fine":
        return f"{regole}\n\n{PERSONA}\n\n{BLOCCO_EMOZIONI_FINE}"
    if variante == "senza-tag":
        return f"{regole}\n\n{PERSONA}"
    raise ValueError(variante)


def chiama(sistema: str, domanda: str, temperatura: float, timeout: int = 600) -> dict:
    corpo = {"model": "ling",
             "messages": [{"role": "system", "content": sistema},
                          {"role": "user", "content": domanda}],
             "temperature": temperatura, "stream": False, "tools": STRUMENTI}
    # NIENTE max_tokens: limitarlo falsa la misura (gia' successo: con 150 il modello
    # esauriva il budget nel ragionamento e sembrava che non rispondesse mai).
    t0 = time.time()
    p = subprocess.run(["curl", "-s", "-m", str(timeout), "-X", "POST", URL,
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(corpo, ensure_ascii=False)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    dt = round(time.time() - t0, 1)
    try:
        d = json.loads(p.stdout)
    except Exception:
        return {"errore": (p.stdout or p.stderr or "")[:200], "secondi": dt}
    msg = ((d.get("choices") or [{}])[0].get("message")) or {}
    return {
        "chiamate": [c.get("function", {}).get("name") for c in (msg.get("tool_calls") or [])],
        "testo": msg.get("content") or "",
        "ragionamento": msg.get("reasoning_content") or "",
        "secondi": dt,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ripetizioni", type=int, default=2)
    ap.add_argument("--varianti", default="tag-inizio,tag-fine,senza-tag")
    ap.add_argument("--temperatura", type=float, default=0.25)
    args = ap.parse_args()

    regole = _regole_vere()
    varianti = [v.strip() for v in args.varianti.split(",") if v.strip()]
    USCITE.mkdir(parents=True, exist_ok=True)
    percorso = USCITE / f"corpus-{datetime.now():%Y%m%d-%H%M%S}.json"

    totale = len(varianti) * len(DOMANDE) * args.ripetizioni
    print(f"{totale} richieste | regole {len(regole)} car | varianti: {', '.join(varianti)}")
    print("nessun limite di max_tokens\n")

    righe = []
    n = 0
    for variante in varianti:
        sistema = costruisci_sistema(variante, regole)
        for dominio, domanda in DOMANDE:
            for r in range(args.ripetizioni):
                n += 1
                e = chiama(sistema, domanda, args.temperatura)
                testo = e.get("testo", "")
                chiamate = e.get("chiamate") or []
                righe.append({
                    "variante": variante, "dominio": dominio, "domanda": domanda,
                    "ripetizione": r, "chiamate": chiamate,
                    "ha_chiamato": bool(chiamate),
                    "doveva_chiamare": dominio != "nessuna",
                    "testo": testo, "ragionamento_car": len(e.get("ragionamento", "")),
                    "secondi": e.get("secondi"), "errore": e.get("errore"),
                })
                stato = "CHIAMA " if chiamate else "risponde"
                print(f"{n:3}/{totale} {variante:11} {dominio:9} {stato} "
                      f"{(','.join(chiamate) or testo[:52].replace(chr(10), ' ')):55} {e.get('secondi')}s",
                      flush=True)
                percorso.write_text(json.dumps(righe, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\ncorpus salvato in {percorso}")
    print("ora: python scripts\\valuta-annunci.py " + str(percorso))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
