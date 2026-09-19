"""Quanto regge la correzione su conversazioni lunghe. Storia reale ricostruita
con get_llm_messages(), poi k scambi di chiacchiera appesi in coda prima della
domanda finale. Se il tasso di chiamata crolla al crescere di k, `recenti=2` e il
troncamento non bastano."""
import importlib.util, json, re, sqlite3, subprocess
from pathlib import Path

URL = "http://127.0.0.1:8012/v1/chat/completions"
RIP = 6
BASE = Path("d:/assistenteeee/odysseus")
CORPO_TMP = Path("d:/vergilius-lab/ricerche/toolcall") / "_corpo_dil.tmp"

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
 _f("manage_memory", "Salva o rilegge memorie.", {"azione": T}, ["azione"]),
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
 _f("fin_insider", "Insider trading.", {"societa": T}, ["societa"]),
 _f("fin_archivio", "Archivio storico finanziario.", {"query": T}, ["query"]),
]

CHIACCHIERA = [
 ("come si scrive 'accelerare', con una c o due?", "[neutral] Con una sola c: accelerare."),
 ("spiegami in due righe cos'e' una cache LRU", "[neutral] Tiene in memoria gli elementi usati di recente e scarta il meno usato quando lo spazio finisce."),
 ("qual e' la differenza tra TCP e UDP?", "[neutral] TCP garantisce ordine e consegna, UDP no ma e' piu' leggero."),
 ("traducimi 'the cat sleeps on the couch'", "[neutral] Il gatto dorme sul divano."),
 ("quanto fa 17 per 23?", "[neutral] 391."),
 ("dammi un sinonimo di 'perentorio'", "[neutral] Categorico."),
 ("cos'e' un decoratore in Python?", "[neutral] Una funzione che ne avvolge un'altra per aggiungerle comportamento."),
 ("meglio tabs o spazi?", "[neutral] Spazi, per convenzione in Python."),
]

c = sqlite3.connect(f'file:{BASE}/data/app.db?mode=ro', uri=True)
righe = list(c.execute(
    "select role, content, metadata from chat_messages "
    "where session_id like 'a1d653b2%' order by timestamp"))
DOMANDA = righe[11][1]

def sessione_con(k):
    s = mm.Session(id='dil', name='d', endpoint_url='u', model='ling')
    s.history = []
    for r, ct, md in righe[:11]:
        try:
            meta = json.loads(md) if md else None
        except Exception:
            meta = None
        s.history.append(mm.ChatMessage(r, ct or "", metadata=meta))
    for i in range(k):
        u, a = CHIACCHIERA[i % len(CHIACCHIERA)]
        s.history.append(mm.ChatMessage("user", u))
        s.history.append(mm.ChatMessage("assistant", a))
    return s

for k in (0, 2, 4, 8):
    s = sessione_con(k)
    storia = s.get_llm_messages()
    car = sum(len(x.get("content") or "") for x in storia)
    esiti = {"chiama": 0, "inventa": 0, "altro": 0, "errore": 0}
    for i in range(RIP):
        corpo = {"model": "ling",
                 "messages": [{"role": "system", "content": SISTEMA}] + storia +
                             [{"role": "user", "content": DOMANDA}],
                 "temperature": 0.25, "stream": False, "tools": STRUMENTI}
        CORPO_TMP.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
        p = subprocess.run(
            ["curl", "-s", "-m", "900", "-X", "POST", URL,
             "-H", "Content-Type: application/json",
             "--data-binary", f"@{CORPO_TMP}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            d = json.loads(p.stdout)
        except Exception:
            esiti["errore"] += 1
            continue
        msg = ((d.get("choices") or [{}])[0].get("message")) or {}
        if msg.get("tool_calls"):
            esiti["chiama"] += 1
        else:
            t = msg.get("content") or ""
            if re.search(r"\d+[.,]\d+\s*%|\$\s?\d|\d{2,3}[.,]\d{3}", t):
                esiti["inventa"] += 1
            else:
                esiti["altro"] += 1
    print(f"+{k:2} scambi di chiacchiera dopo l'ultimo turno con strumenti  "
          f"({len(storia):2} msg, {car:6} car)  chiama {esiti['chiama']}/{RIP}  "
          f"INVENTA {esiti['inventa']}  altro {esiti['altro']}  err {esiti['errore']}",
          flush=True)
