"""Chiarisce una discrepanza.

Sulla domanda che ha fatto partire tutto — "a livello financial invece che
novita' abbiamo?" — due misure danno risposte diverse con la storia fedele:

  test isolato del 26 ago, notte : 6/8   troncamento 2000 car, nessun tetto ai token
  suite storia x temperatura     : 1/3   troncamento 1500/300, max_tokens 4096

Tre differenze sovrapposte: quanto si tronca l'output degli strumenti nella
storia, il tetto ai token in uscita, e il numero di ripetizioni. Qui si separano,
12 ripetizioni per cella, tutto il resto identico.
"""
import argparse, importlib.util, json, re, sqlite3, subprocess, time
from datetime import datetime
from pathlib import Path

BASE = Path("d:/assistenteeee/odysseus")
USCITA = Path("d:/vergilius-lab/ricerche/toolcall")
URL = "http://127.0.0.1:8012/v1/chat/completions"

ap = argparse.ArgumentParser()
ap.add_argument("--ripetizioni", type=int, default=12)
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

c = sqlite3.connect(f'file:{BASE}/data/app.db?mode=ro', uri=True)
righe = list(c.execute(
    "select role, content, metadata from chat_messages "
    "where session_id like 'a1d653b2%' order by timestamp"))
DOMANDA = righe[11][1]

sess = mm.Session(id='fn', name='f', endpoint_url='u', model=args.modello)
sess.history = []
for r, ct, md in righe[:11]:
    try:
        meta = json.loads(md) if md else None
    except Exception:
        meta = None
    sess.history.append(mm.ChatMessage(r, ct or "", metadata=meta))

CELLE = [
 # nome                              storia                                                   max_tokens
 ("prosa (riferimento)",             sess.get_context_messages(),                             4096),
 ("fedele 1500/300 + 4096 tok",      sess.get_llm_messages(),                                 4096),
 ("fedele 2000/2000 + 4096 tok",     sess.get_llm_messages(2000, 2000, recenti=99),           4096),
 ("fedele 1500/300 + 16384 tok",     sess.get_llm_messages(),                                16384),
 ("fedele 2000/2000 + 16384 tok",    sess.get_llm_messages(2000, 2000, recenti=99),          16384),
]

NUMERI = re.compile(r"\d+[.,]\d+\s*%|\$\s?\d|\d{2,3}[.,]\d{3}")
USCITA.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
fout = USCITA / f"suite-fin-novita-{stamp}.json"
CORPO = fout.with_suffix(".corpo.tmp")
dati = {"modello": args.modello, "domanda": DOMANDA,
        "ripetizioni": args.ripetizioni, "risposte": []}

totale = len(CELLE) * args.ripetizioni
n = 0
t_inizio = time.time()
print(f"fin-novita: {totale} risposte -> {fout}", flush=True)
print(f"domanda: {DOMANDA!r}\n", flush=True)

for nome, storia, maxtok in CELLE:
    car = sum(len(x.get("content") or "") for x in storia)
    esiti = {"chiama": 0, "inventa": 0, "risponde": 0, "errore": 0}
    quali = []
    for giro in range(args.ripetizioni):
        n += 1
        corpo = {"model": args.modello,
                 "messages": ([{"role": "system", "content": SISTEMA}] + storia +
                              [{"role": "user", "content": DOMANDA}]),
                 "temperature": 0.25, "stream": False,
                 "tools": STRUMENTI, "max_tokens": maxtok}
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
            esito, strumento = "errore", None
        elif msg.get("tool_calls"):
            strumento = msg["tool_calls"][0]["function"]["name"]
            esito = "chiama"
            quali.append(strumento)
        else:
            strumento = None
            esito = "inventa" if NUMERI.search(msg.get("content") or "") else "risponde"
        esiti[esito] += 1
        dati["risposte"].append({"cella": nome, "giro": giro, "esito": esito,
                                 "strumento": strumento, "secondi": round(dt, 1)})
        fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        resta = (time.time() - t_inizio) / max(n, 1) * (totale - n)
        print(f"[{n:3}/{totale}] {nome:30} {giro+1:2}/{args.ripetizioni} "
              f"{esito.upper():8} {strumento or '':16} {dt:5.1f}s  "
              f"restano ~{resta/60:.0f} min", flush=True)
    strum = ", ".join(sorted(set(quali))) if quali else "-"
    print(f"  ==> {nome:30} ({len(storia):2} msg, {car:6} car)  "
          f"chiama {esiti['chiama']}/{args.ripetizioni}  INVENTA {esiti['inventa']}  "
          f"risponde {esiti['risponde']}  err {esiti['errore']}  [{strum}]\n", flush=True)

try:
    CORPO.unlink()
except Exception:
    pass
print(f"finito -> {fout}", flush=True)
