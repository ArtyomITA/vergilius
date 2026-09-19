r"""Banco delle chiamate a strumenti: quante volte il modello AGISCE invece di rispondere a memoria.

Perche' esiste: il 26 ago 2026 il modello ha risposto a "a livello financial che novita'
abbiamo?" con un riepilogo di mercati INVENTATO, pur avendo `fin_mercati` e `osint_notizie`
fra i 12 strumenti inviati, e senza emettere nessuna chiamata (log: `0 native calls`).
Una risposta inventata e' indistinguibile da una documentata: e' il difetto piu' pericoloso
di tutti, perche' non si vede.

Cosa misura: su una batteria di domande che DEVONO produrre una chiamata, la percentuale di
volte in cui la chiamata avviene davvero, al variare del prompt di sistema e della temperatura.

Uso:
  odysseus\venv\Scripts\python.exe scripts\banco-toolcall.py                 # tutte le varianti
  odysseus\venv\Scripts\python.exe scripts\banco-toolcall.py --ripetizioni 5
  odysseus\venv\Scripts\python.exe scripts\banco-toolcall.py --varianti attuale,senza-emozioni

Esito: JSON in ricerche/toolcall/ + tabella a schermo. Non tocca nulla in produzione:
parla con llama-swap (8012) come farebbe Odysseus, ma senza passare da Odysseus.
"""

from __future__ import annotations

import argparse
import json
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

# --------------------------------------------------------------------------- strumenti
# Gli stessi 12 che Odysseus ha inviato nel turno fallito (log 02:40:01), con gli schemi
# ridotti all'essenziale: qui si misura SE chiama, non quanto bene compila gli argomenti.
def _f(nome: str, descrizione: str, prop: dict, obbligatori: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": nome, "description": descrizione,
        "parameters": {"type": "object", "properties": prop, "required": obbligatori}}}


TESTO = {"type": "string"}
STRUMENTI = [
    _f("fin_mercati", "Prezzi, indici e dati di mercato in tempo reale (azioni, cripto, valute).",
       {"simbolo": TESTO}, ["simbolo"]),
    _f("fin_notizie", "Notizie finanziarie recenti su un tema o un titolo.", {"tema": TESTO}, ["tema"]),
    _f("fin_insider", "Operazioni di insider trading dichiarate.", {"societa": TESTO}, ["societa"]),
    _f("fin_appalti", "Appalti e contratti pubblici.", {"ente": TESTO}, ["ente"]),
    _f("osint_notizie", "Notizie di attualita' e geopolitica dai feed OSINT.", {"tema": TESTO}, ["tema"]),
    _f("osint_web", "Ricerca sul web aperto.", {"query": TESTO}, ["query"]),
    _f("osint_dettaglio", "Approfondisce un evento OSINT gia' individuato.", {"id_evento": TESTO}, ["id_evento"]),
    _f("osint_mappa", "Eventi OSINT su area geografica.", {"area": TESTO}, ["area"]),
    _f("web_search", "Ricerca web generica per un fatto puntuale.", {"query": TESTO}, ["query"]),
    _f("manage_memory", "Salva o rilegge memorie dell'utente.", {"azione": TESTO}, ["azione"]),
    _f("ask_user", "Chiede un chiarimento all'utente.", {"domanda": TESTO}, ["domanda"]),
    _f("update_plan", "Aggiorna il piano di lavoro.", {"passi": TESTO}, ["passi"]),
]

# --------------------------------------------------------------------------- casi
# Ogni caso DEVE produrre una chiamata: chiede dati freschi che il modello non puo' sapere.
# `attesi` = strumenti accettabili; se ne chiama uno di quelli, e' un successo pieno.
CASI = [
    ("fin-novita",   "A livello financial invece che novità abbiamo?",
     {"fin_mercati", "fin_notizie", "osint_notizie", "osint_web", "web_search"}),
    ("fin-prezzo",   "Quanto vale Apple in questo momento?",
     {"fin_mercati", "web_search", "osint_web"}),
    ("fin-cripto",   "Com'è messo bitcoin oggi?",
     {"fin_mercati", "web_search", "osint_web"}),
    ("fin-insider",  "Ci sono operazioni insider recenti su Nvidia?",
     {"fin_insider", "fin_notizie", "web_search", "osint_web"}),
    ("osint-mondo",  "Che è successo nel mondo nelle ultime due ore?",
     {"osint_notizie", "osint_mappa", "osint_web", "web_search"}),
    ("osint-area",   "Situazione nello stretto di Hormuz adesso?",
     {"osint_notizie", "osint_mappa", "osint_web", "web_search"}),
    ("web-fatto",    "Chi ha vinto l'ultima gara di Formula 1?",
     {"web_search", "osint_web", "osint_notizie"}),
    ("web-prezzo",   "Quanto costa oggi un barile di Brent?",
     {"fin_mercati", "web_search", "osint_web"}),
]

# --------------------------------------------------------------------------- varianti di prompt
BASE_PERSONA = "assistente di adrian chiamata mao"

BLOCCO_EMOZIONI = """<!-- avatar-emotions -->
Hai un volto animato che mostra le tue emozioni. Inserisci UN tag emozione
all'inizio di ogni risposta, e cambialo durante la risposta solo se il tono cambia
davvero. Tag disponibili: [neutral] [fear] [sadness] [anger] [disgust] [joy] [smirk] [surprise]
Scrivi il tag esattamente così, fra parentesi quadre, senza spiegarlo mai
all'utente. Esempio: "[joy] Trovato! Il file era nella cartella temporanea."
Usa [neutral] quando non c'è una emozione particolare."""

REGOLA_STRUMENTI = (
    "Hai strumenti per consultare dati in tempo reale. Per qualunque informazione che cambia "
    "nel tempo (prezzi, notizie, eventi, quotazioni) DEVI chiamare uno strumento: non rispondere "
    "mai a memoria, perche' i tuoi dati sono vecchi e inventeresti."
)

# Le REGOLE VERE di Odysseus (14290 caratteri, ~3572 token). Il turno fallito aveva 6081
# token di prompt: senza queste il banco misura una situazione che in produzione non esiste.
def _regole_vere() -> str:
    import re
    try:
        src = (WORKSPACE / "odysseus" / "src" / "agent_loop.py").read_text(encoding="utf-8")
        m = re.search(
            "_API_AGENT_RULES" + r"\s*=\s*" + '(?:r?"""|' + r"r?''')" + "(.*?)" + '(?:"""|' + r"''')",
            src, re.S)
        return m.group(1) if m else ""
    except Exception:
        return ""


REGOLE_ODYSSEUS = _regole_vere()

VARIANTI = {
    # Com'e' oggi in produzione: persona + blocco emozioni dell'Avatar 2D.
    "attuale":          f"{BASE_PERSONA}\n\n{BLOCCO_EMOZIONI}",
    # Stessa persona, senza il blocco che impone un tag a inizio risposta.
    "senza-emozioni":   BASE_PERSONA,
    # Nessun prompt di sistema: il comportamento nudo del modello.
    "nudo":             "",
    # Persona + una regola esplicita sull'uso degli strumenti.
    "con-regola":       f"{BASE_PERSONA}\n\n{REGOLA_STRUMENTI}",
    # Il caso peggiore ipotizzato: emozioni E regola insieme, per vedere se la regola recupera.
    "emozioni+regola":  f"{BASE_PERSONA}\n\n{BLOCCO_EMOZIONI}\n\n{REGOLA_STRUMENTI}",
    # --- con le REGOLE VERE di Odysseus: e' questo che gira davvero in produzione ---
    "reale":             f"{REGOLE_ODYSSEUS}\n\n{BASE_PERSONA}\n\n{BLOCCO_EMOZIONI}",
    "reale-no-emozioni": f"{REGOLE_ODYSSEUS}\n\n{BASE_PERSONA}",
    "reale+regola":      f"{REGOLE_ODYSSEUS}\n\n{BASE_PERSONA}\n\n{BLOCCO_EMOZIONI}\n\n{REGOLA_STRUMENTI}",
}


def chiama(sistema: str, domanda: str, temperatura: float, max_tok: int, timeout: int = 300) -> dict:
    messaggi = []
    if sistema:
        messaggi.append({"role": "system", "content": sistema})
    messaggi.append({"role": "user", "content": domanda})
    corpo = {"model": "ling", "messages": messaggi, "max_tokens": max_tok,
             "temperature": temperatura, "stream": False, "tools": STRUMENTI}
    t0 = time.time()
    p = subprocess.run(
        ["curl", "-s", "-m", str(timeout), "-X", "POST", URL,
         "-H", "Content-Type: application/json", "-d", json.dumps(corpo, ensure_ascii=False)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    dt = time.time() - t0
    try:
        d = json.loads(p.stdout)
    except Exception:
        return {"errore": (p.stdout or p.stderr or "")[:200], "secondi": round(dt, 1)}
    msg = ((d.get("choices") or [{}])[0].get("message")) or {}
    chiamate = [c.get("function", {}).get("name") for c in (msg.get("tool_calls") or [])]
    return {
        "chiamate": [c for c in chiamate if c],
        "testo": (msg.get("content") or "")[:400],
        "ragionamento": len(msg.get("reasoning_content") or ""),
        "secondi": round(dt, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ripetizioni", type=int, default=3)
    ap.add_argument("--varianti", default=",".join(VARIANTI))
    ap.add_argument("--temperatura", type=float, default=0.25,
                    help="0.25 = quella che Odysseus usa nei giri con strumenti")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--casi", default="", help="sottoinsieme, separati da virgola")
    args = ap.parse_args()

    varianti = [v.strip() for v in args.varianti.split(",") if v.strip() in VARIANTI]
    casi = [c for c in CASI if not args.casi or c[0] in args.casi.split(",")]
    if not varianti or not casi:
        print("nessuna variante o nessun caso selezionato"); return 2

    USCITE.mkdir(parents=True, exist_ok=True)
    percorso = USCITE / f"toolcall-{datetime.now():%Y%m%d-%H%M%S}.json"
    righe = []
    totale = len(varianti) * len(casi) * args.ripetizioni
    print(f"{totale} richieste: {len(varianti)} varianti x {len(casi)} casi x {args.ripetizioni} ripetizioni")
    print(f"temperatura {args.temperatura}, max_tokens {args.max_tokens}")
    for v in varianti:
        n_car = len(VARIANTI[v])
        print(f"    {v:20} prompt di sistema {n_car:6} caratteri (~{n_car // 4} token)")
    print()

    n = 0
    for variante in varianti:
        sistema = VARIANTI[variante]
        for nome_caso, domanda, attesi in casi:
            for r in range(args.ripetizioni):
                n += 1
                esito = chiama(sistema, domanda, args.temperatura, args.max_tokens)
                chiamate = esito.get("chiamate") or []
                colpito = bool(set(chiamate) & attesi)
                riga = {"variante": variante, "caso": nome_caso, "ripetizione": r,
                        "chiamate": chiamate, "atteso": sorted(attesi), "colpito": colpito,
                        "secondi": esito.get("secondi"), "errore": esito.get("errore"),
                        "ragionamento_car": esito.get("ragionamento"),
                        "testo": esito.get("testo")}
                righe.append(riga)
                simbolo = "OK " if colpito else ("-- " if not chiamate else "?? ")
                print(f"{n:3}/{totale} {simbolo} {variante:16} {nome_caso:12} "
                      f"{','.join(chiamate) or 'NESSUNA CHIAMATA':40} {esito.get('secondi')}s", flush=True)
                percorso.write_text(json.dumps(righe, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 74)
    print(f"{'variante':18} {'chiama giusto':>14} {'chiama sbagliato':>17} {'non chiama':>12}")
    for variante in varianti:
        r = [x for x in righe if x["variante"] == variante]
        ok = sum(1 for x in r if x["colpito"])
        sbagliato = sum(1 for x in r if x["chiamate"] and not x["colpito"])
        niente = sum(1 for x in r if not x["chiamate"])
        print(f"{variante:18} {ok:>6}/{len(r):<7} {sbagliato:>17} {niente:>12}")
    print("=" * 74)
    print(f"\nesito completo in {percorso}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
