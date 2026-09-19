"""Suite: storia x temperatura x caso.

Due assi, piu' un banco di casi che misura entrambe le direzioni dell'errore.

STORIA
  prosa   = get_context_messages(), quello che Odysseus mandava prima:
            nessun tool_calls, nessun role:"tool". Il modello vede sé stesso
            rispondere sempre a braccio.
  fedele  = get_llm_messages(), la correzione: le chiamate e i risultati dei
            turni precedenti ricostruiti da metadata["tool_events"].

TEMPERATURA
  Ling raccomanda temperature 1.0, top_p 0.95, top_k 20. top_p e top_k li
  abbiamo gia' uguali (li impone il server via --top-p/--top-k; Odysseus non li
  manda per i modelli non-MiniMax). L'unica deviazione e' la temperatura:
  agent_loop.py taglia a 0.25 quando ci sono strumenti
  (`_temp_giro = min(temperature, 0.25) if all_tool_schemas`).

CASI
  Otto che DEVONO produrre una chiamata (dati che cambiano nel tempo, o una
  preferenza da salvare) e quattro che NON devono (risposte che stanno nella
  conoscenza del modello). Serve misurare tutte e due le direzioni: alzare la
  temperatura potrebbe far chiamare di piu' e anche chiamare a sproposito.

Riprende da dove si era fermata: i risultati si scrivono man mano su disco.
Una riga di avanzamento per ogni singola risposta.
"""
import argparse, importlib.util, json, re, sqlite3, subprocess, sys, time
from datetime import datetime
from pathlib import Path

BASE = Path("d:/assistenteeee/odysseus")
USCITA = Path("d:/vergilius-lab/ricerche/toolcall")
URL = "http://127.0.0.1:8012/v1/chat/completions"
MAX_TOKENS = 4096  # quello che manda davvero agent_loop nei giri agentici

ap = argparse.ArgumentParser()
ap.add_argument("--ripetizioni", type=int, default=3)
ap.add_argument("--riprendi", type=str, default=None,
                help="file JSON di una corsa interrotta")
ap.add_argument("--modello", type=str, default="ling")
args = ap.parse_args()

spec = importlib.util.spec_from_file_location("modelli", BASE / "core/models.py")
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

src = (BASE / "src/agent_loop.py").read_text(encoding="utf-8")
m = re.search("_API_AGENT_RULES" + r"\s*=\s*" + '(?:r?"""|' + r"r?''')" + "(.*?)" + '(?:"""|' + r"''')", src, re.S)
REGOLE = m.group(1) if m else ""
MEMORIE = ("Memorie sull'utente:\n- The user speaks Italian.\n"
           "- L'utente e' interessato ai mercati finanziari.\n- Preferisce l'italiano.\n")
SISTEMA = (REGOLE + "\n\nassistente di adrian chiamata mao\n\n<!-- avatar-emotions -->\n"
           "Inserisci UN tag emozione all'inizio di ogni risposta. Tag: [neutral] [joy] [anger]\n\n" + MEMORIE)


def _f(n, d, p, r):
    return {"type": "function", "function": {"name": n, "description": d,
            "parameters": {"type": "object", "properties": p, "required": r}}}


T = {"type": "string"}
STRUMENTI = [
 _f("manage_memory", "Salva o rilegge memorie e preferenze dell'utente.", {"azione": T}, ["azione"]),
 _f("ask_user", "Chiede chiarimenti.", {"domanda": T}, ["domanda"]),
 _f("update_plan", "Aggiorna il piano.", {"passi": T}, ["passi"]),
 _f("trigger_research", "Ricerca approfondita.", {"tema": T}, ["tema"]),
 _f("osint_notizie", "Notizie di attualita' e geopolitica.", {"tema": T}, ["tema"]),
 _f("osint_situazione", "Quadro globale di situazione.", {"quanti": T}, ["quanti"]),
 _f("osint_dettaglio", "Approfondisce un evento.", {"id_evento": T}, ["id_evento"]),
 _f("osint_mappa", "Eventi su area geografica.", {"area": T}, ["area"]),
 _f("osint_web", "Ricerca sul web aperto.", {"query": T}, ["query"]),
 _f("fin_mercati", "Prezzi e dati di mercato in tempo reale.", {"simbolo": T}, ["simbolo"]),
 _f("fin_appalti", "Appalti pubblici.", {"ente": T}, ["ente"]),
 _f("fin_insider", "Insider trading e operazioni di societa' quotate.", {"societa": T}, ["societa"]),
 _f("fin_archivio", "Archivio storico finanziario.", {"query": T}, ["query"]),
]

CASI = [
 ("fin-novita",   "a livello financial invece che novita' abbiamo?", True),
 ("fin-prezzo",   "quanto sta AAPL adesso?", True),
 ("fin-insider",  "ci sono operazioni insider recenti su Leonardo?", True),
 ("fin-appalti",  "quali appalti ha pubblicato il Comune di Roma di recente?", True),
 ("osint-oggi",   "cosa e' successo di grosso nel mondo oggi?", True),
 ("osint-zona",   "ci sono eventi rilevanti in Medio Oriente in questo momento?", True),
 ("web-cerca",    "cerca sul web cosa dicono dell'ultimo taglio dei tassi della BCE", True),
 ("memoria",      "ricordati che d'ora in poi voglio le risposte piu' corte", True),
 ("no-lru",       "spiegami in due righe cos'e' una cache LRU", False),
 ("no-mat",       "quanto fa 17 per 23?", False),
 ("no-trad",      "traducimi 'the cat sleeps on the couch'", False),
 ("no-tcp",       "qual e' la differenza tra TCP e UDP?", False),
]

TEMPERATURE = [
 ("0,25 taglio agent_loop", 0.25),
 ("0,60 intermedia",        0.60),
 ("1,00 raccomandata Ling", 1.00),
]

# --- storia reale dal DB, nelle due forme ---
c = sqlite3.connect(f'file:{BASE}/data/app.db?mode=ro', uri=True)
righe = list(c.execute(
    "select role, content, metadata from chat_messages "
    "where session_id like 'a1d653b2%' order by timestamp"))
sess = mm.Session(id='suite', name='s', endpoint_url='u', model=args.modello)
sess.history = []
for r, ct, md in righe[:11]:
    try:
        meta = json.loads(md) if md else None
    except Exception:
        meta = None
    sess.history.append(mm.ChatMessage(r, ct or "", metadata=meta))

STORIE = {
    "prosa":  sess.get_context_messages(),
    "fedele": sess.get_llm_messages(),
}

NUMERI = re.compile(r"\d+[.,]\d+\s*%|\$\s?\d|\d{2,3}[.,]\d{3}")

USCITA.mkdir(parents=True, exist_ok=True)
if args.riprendi:
    fout = Path(args.riprendi)
    dati = json.loads(fout.read_text(encoding="utf-8"))
    print(f"riprendo da {fout.name}: {len(dati['risposte'])} risposte gia' fatte", flush=True)
else:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fout = USCITA / f"suite-storia-temperatura-{stamp}.json"
    dati = {"modello": args.modello, "max_tokens": MAX_TOKENS,
            "ripetizioni": args.ripetizioni, "risposte": []}

fatte = {(r["storia"], r["temperatura"], r["caso"], r["giro"]) for r in dati["risposte"]}
CORPO = fout.with_suffix(".corpo.tmp")

totale = len(STORIE) * len(TEMPERATURE) * len(CASI) * args.ripetizioni
n = 0
t_inizio = time.time()
print(f"suite: {totale} risposte in totale -> {fout}", flush=True)

for ns, storia in STORIE.items():
    for nt, temp in TEMPERATURE:
        for cid, domanda, deve in CASI:
            for giro in range(args.ripetizioni):
                n += 1
                chiave = (ns, nt, cid, giro)
                if chiave in fatte:
                    continue
                corpo = {
                    "model": args.modello,
                    "messages": ([{"role": "system", "content": SISTEMA}] + storia +
                                 [{"role": "user", "content": domanda}]),
                    "temperature": temp,
                    "stream": False,
                    "tools": STRUMENTI,
                    "max_tokens": MAX_TOKENS,
                }
                CORPO.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
                t0 = time.time()
                p = subprocess.run(
                    ["curl", "-s", "-m", "300", "-X", "POST", URL,
                     "-H", "Content-Type: application/json",
                     "--data-binary", f"@{CORPO}"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                dt = time.time() - t0
                try:
                    d = json.loads(p.stdout)
                    msg = ((d.get("choices") or [{}])[0].get("message")) or {}
                except Exception:
                    msg = None

                if msg is None:
                    esito, strumento, testo = "ERRORE", None, ""
                elif msg.get("tool_calls"):
                    strumento = msg["tool_calls"][0]["function"]["name"]
                    esito = "chiama"
                    testo = ""
                else:
                    strumento = None
                    testo = msg.get("content") or ""
                    esito = "inventa" if (deve and NUMERI.search(testo)) else "risponde"

                dati["risposte"].append({
                    "storia": ns, "temperatura": nt, "caso": cid,
                    "deve_chiamare": deve, "giro": giro, "esito": esito,
                    "strumento": strumento, "secondi": round(dt, 1),
                    "testo": testo[:400],
                })
                fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")

                atteso = "deve" if deve else "NON deve"
                marchio = {"chiama": "CHIAMA", "inventa": "INVENTA",
                           "risponde": "risponde", "ERRORE": "ERRORE"}[esito]
                resta = (time.time() - t_inizio) / max(n, 1) * (totale - n)
                print(f"[{n:3}/{totale}] {ns:6} {nt:24} {cid:12} ({atteso:8}) "
                      f"{marchio:9} {strumento or '':16} {dt:5.1f}s  "
                      f"restano ~{resta/60:.0f} min", flush=True)

try:
    CORPO.unlink()
except Exception:
    pass
print(f"\nfinito. {len(dati['risposte'])} risposte in {fout}", flush=True)
print(f"ora: python scripts/leggi-suite.py {fout}", flush=True)
