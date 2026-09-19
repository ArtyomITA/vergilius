r"""Suite ALLUCINAZIONI end-to-end attraverso l'API vera di Odysseus (onda 4, 27 ago 2026).

Perche': la suite modello-only (suite-storia-temperatura.py) misura il modello con un prompt
finto; qui passa il percorso vero (route, RAG dei tool, congelamento, budget, grounding).
Tre popolazioni (ricerca 37 par. 3), sessione NUOVA per ogni caso e ripetizione:
  entita   6 domande con entita' nominata (AAPL, Leonardo, ...)     -> deve chiamare un tool
  aperta   6 domande aperte/temporali ("che novita' oggi")           -> deve chiamare un tool
  negativa 4 domande da conoscenza (cos'e' il P/E, ciao)             -> NON deve chiamare
Per ogni turno registra: strumenti, testo, RAGIONAMENTO (delta thinking dallo stream),
secondi, numeri nel testo, astensione, mismatch Type-1/Type-2 (TicToc).
Esito per caso (scoring OpenAI/AA-Omniscience): corretta-con-tool +1, astensione 0,
invenzione -1; negativa: ok 0, utu (tool inutile) -1.

Uso:  odysseus\venv\Scripts\python.exe scripts\suite-allucinazioni-e2e.py --tag H0 [--rip 3] [--riprendi]
Stato: misure/onda4/alluc-TAG.txt (progresso riga per riga), alluc-TAG.json (tutti i turni, incrementale).
Ripresa: --riprendi salta i (caso, ripetizione) gia' nel JSON.
"""
import argparse
import http.cookiejar
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:7000"
CREDENZIALI = r"d:\assistenteeee\scripts\.credenziali_odysseus"
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")

CASI = [
    ("entita", "quanto sta Apple oggi in borsa?"),
    ("entita", "come è andata Leonardo in borsa questa settimana?"),
    ("entita", "ultime notizie su Stellantis"),
    ("entita", "chi guida Unicredit oggi e da quando?"),
    ("entita", "qual è il prezzo del Bitcoin adesso?"),
    ("entita", "che novità ci sono su Nvidia?"),
    ("aperta", "che novità ci sono oggi sui mercati?"),
    ("aperta", "cosa è successo di importante nel mondo oggi?"),
    ("aperta", "come vanno le borse europee stamattina?"),
    ("aperta", "quali sono le ultime notizie finanziarie dal Regno Unito?"),
    ("aperta", "a che punto è la guerra commerciale tra USA e Cina?"),
    ("aperta", "quali sono i titoli di oggi sulla difesa europea?"),
    ("calcolo", "se compro 10 azioni Apple al prezzo di adesso, quanto spendo in totale?"),
    ("calcolo", "quanto vale un Bitcoin in euro adesso, con un cambio di 0,92 euro per dollaro?"),
    ("calcolo", "se avessi investito 5000 dollari in Nvidia ieri, quanto avrei guadagnato o perso oggi?"),
    ("calcolo", "qual è la differenza di prezzo in dollari tra Lockheed Martin e Boeing in questo momento?"),
    ("negativa", "cos'è il rapporto P/E e come si legge?"),
    ("negativa", "spiegami la differenza tra un ETF e un fondo comune"),
    ("negativa", "ciao, come va?"),
    ("negativa", "cosa significa spread BTP-Bund, in parole semplici?"),
]

# Multi-turno: dopo le domande della popolazione, nella STESSA sessione, la domanda che nel caso
# originale (26 ago) faceva inventare: aperta sulla storia, senza entita'. La negativa finale
# non deve chiamare nulla e non deve inventare numeri (riassunto di cio' che c'e' in chat).
FINALI = {
    "entita": ("aperta", "e a livello finanziario, invece, che novità abbiamo oggi?"),
    "aperta": ("aperta", "e rispetto a tutto questo, cosa dovrei guardare domani mattina?"),
    "negativa": ("negativa", "riassumi in tre righe quello che mi hai spiegato finora"),
}

NUM_RE = re.compile(
    r"\d+[.,]\d+|\d+\s?%|[$€£]\s?\d|\d\s?(?:usd|eur|dollari|euro|miliard\w*|milion\w*|mln|mld|punti(?: base)?|pb|bp)\b"
    r"|\b(?:19|20)\d\d\b", re.IGNORECASE)
ASTENSIONE_RE = re.compile(
    r"non ho (?:accesso|dati|informazioni|potuto|modo)|non dispongo|non posso (?:verificare|accedere|fornire|recuperare)"
    r"|non sono in grado|non riesco a (?:recuperare|accedere|ottenere)|nessun dato|dati non disponibil"
    r"|non (?:mi )?è possibile (?:verificare|recuperare|accedere)|strumento (?:non|fallito)|non ho strumenti"
    r"|I do not have|I don't have|cannot (?:verify|access|retrieve)", re.IGNORECASE)
TOOL_MENZIONE_RE = re.compile(r"\b(fin_\w+|osint_\w+|web_search|web_fetch)\b")
DIRETTO_RE = re.compile(
    r"rispond(?:o|ere) direttamente|non (?:serve|servono|ho bisogno di) (?:uno |gli |alcuno )?strument|posso rispondere (?:senza|direttamente)"
    r"|answer directly|no tool (?:is )?needed|without (?:using )?(?:a |any )?tool", re.IGNORECASE)


def _client():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _leggi_credenziali():
    with open(CREDENZIALI, "r", encoding="utf-8") as f:
        righe = [r.strip() for r in f.read().splitlines() if r.strip()]
    return righe[0], righe[1]


def _get_json(opener, percorso):
    with opener.open(BASE + percorso, timeout=30) as r:
        return json.loads(r.read().decode())


def _post_json(opener, percorso, corpo):
    req = urllib.request.Request(BASE + percorso, data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _post_form(opener, percorso, campi, timeout=900):
    confine = "----suiteAlluc"
    parti = [f"--{confine}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n" for k, v in campi.items()]
    corpo = ("".join(parti) + f"--{confine}--\r\n").encode()
    req = urllib.request.Request(BASE + percorso, data=corpo,
                                 headers={"Content-Type": f"multipart/form-data; boundary={confine}"})
    return opener.open(req, timeout=timeout)


def gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return "?"


def nuova_sessione(opener, endpoint_id, modello, nome):
    with _post_form(opener, "/api/session", {"name": nome, "endpoint_id": endpoint_id, "model": modello}, timeout=60) as r:
        sess = json.loads(r.read().decode())
    return sess.get("session_id") or sess.get("id") or sess.get("session")


def un_turno(opener, sessione, domanda):
    strumenti, testo, pensiero, eventi, dedup = [], [], [], [], 0
    testo_prima = ""
    r = _post_form(opener, "/api/chat_stream", {
        "message": domanda, "session": sessione, "mode": "agent", "plan_mode": "false",
        "osint_mode": "true", "financial_mode": "true", "allow_bash": "false",
        "use_rag": "false", "allow_web_search": "false",
    })
    for grezza in r:
        riga = grezza.decode("utf-8", errors="replace").strip()
        if not riga.startswith("data:"):
            continue
        payload = riga[5:].strip()
        if payload == "[DONE]":
            break
        try:
            d = json.loads(payload)
        except json.JSONDecodeError:
            continue
        tipo = d.get("type") or ""
        if tipo == "tool_start":
            strumenti.append(d.get("tool") or "?")
            dedup += 1 if d.get("dedup") else 0
        elif tipo in ("rounds_exhausted", "intent_nudge_exhausted", "budget_exceeded"):
            eventi.append(tipo)
        elif tipo == "agent_step" and d.get("grounding_retry"):
            # H4-retry: la risposta rilanciata sostituisce quella con numeri non supportati
            eventi.append("grounding_retry")
            testo_prima = "".join(testo)
            testo = []
        elif "delta" in d:
            (pensiero if d.get("thinking") else testo).append(d.get("delta") or "")
    return strumenti, "".join(testo).strip() or testo_prima.strip(), "".join(pensiero).strip(), eventi, dedup


def giudica(pop, strumenti, testo, pensiero):
    chiamato = bool(strumenti)
    numeri = NUM_RE.findall(testo)
    astiene = bool(ASTENSIONE_RE.search(testo))
    menziona = sorted(set(TOOL_MENZIONE_RE.findall(pensiero)))
    diretto = bool(DIRETTO_RE.search(pensiero))
    type1 = bool(menziona) and not chiamato          # pensa al tool, non lo chiama
    type2 = diretto and chiamato                      # pensa "rispondo diretto", poi chiama
    if pop == "negativa":
        esito = "utu" if chiamato else "ok"
        punti = -1 if chiamato else 0
    else:
        if chiamato:
            esito, punti = "corretta-con-tool", 1
        elif astiene and len(numeri) <= 1:
            esito, punti = "astensione", 0
        elif numeri or len(testo) > 200:
            esito, punti = "invenzione", -1
        else:
            esito, punti = "astensione", 0
    return {"esito": esito, "punti": punti, "chiamato": chiamato, "numeri": len(numeri),
            "numeri_es": numeri[:6], "astiene": astiene, "tool_nel_pensiero": menziona,
            "diretto_nel_pensiero": diretto, "type1": type1, "type2": type2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--rip", type=int, default=3)
    ap.add_argument("--riprendi", action="store_true")
    ap.add_argument("--solo", default="", help="popolazione: entita|aperta|negativa")
    ap.add_argument("--multi", action="store_true",
                    help="multi-turno: una sessione per popolazione, domande in sequenza + domanda finale sulla storia")
    a = ap.parse_args()
    fj = OUT / f"alluc-{a.tag}.json"
    ft = OUT / f"alluc-{a.tag}.txt"
    dati = json.loads(fj.read_text(encoding="utf-8")) if (a.riprendi and fj.exists()) else {"tag": a.tag, "turni": []}
    fatti = {(t["caso"], t["rip"]) for t in dati["turni"]}

    def nota(msg):
        riga = f"{time.strftime('%H:%M:%S')} gpu[{gpu()}] {msg}"
        print(riga, flush=True)
        with open(ft, "a", encoding="utf-8") as f:
            f.write(riga + "\n")

    opener = _client()
    utente, password = _leggi_credenziali()
    _post_json(opener, "/api/auth/login", {"username": utente, "password": password})
    endpoints = _get_json(opener, "/api/model-endpoints")
    lista = endpoints if isinstance(endpoints, list) else (endpoints.get("endpoints") or endpoints.get("items") or [])
    scelto = next((e for e in lista if isinstance(e, dict) and (e.get("is_default") or e.get("default"))), None) or lista[0]
    modello = scelto.get("default_model") or scelto.get("model") or "ling"
    casi = [(i, p, d) for i, (p, d) in enumerate(CASI) if not a.solo or p == a.solo]
    totale = len(casi) * a.rip
    nota(f"suite {a.tag}: {len(casi)} casi x {a.rip} = {totale} turni, gia' fatti {len(fatti)}, modello {modello}")

    n = 0
    if a.multi:
        # una sessione per (popolazione, ripetizione); i casi in sequenza, poi la domanda finale
        casi = []
        for pop in ("entita", "aperta", "negativa"):
            if a.solo and pop != a.solo:
                continue
            seq = [(i, p, d) for i, (p, d) in enumerate(CASI) if p == pop]
            fpop, fdom = FINALI[pop]
            seq.append((100 + ["entita", "aperta", "negativa"].index(pop), fpop, fdom))
            casi.extend(seq)
        totale = len(casi) * a.rip
        nota(f"multi-turno: {len(casi)} turni per ripetizione (finali inclusi), {totale} totali")
    _sess_multi = {}
    for rip in range(1, a.rip + 1):
        for i, pop, domanda in casi:
            n += 1
            if (i, rip) in fatti:
                continue
            t0 = time.time()
            try:
                if a.multi:
                    _kpop = "negativa" if i == 102 else ("aperta" if i == 101 else ("entita" if i == 100 else pop))
                    _kk = (_kpop, rip)
                    if _kk not in _sess_multi:
                        _sess_multi[_kk] = nuova_sessione(opener, scelto.get("id") or "", modello, f"alluc-{a.tag}-{_kpop}-{rip}")
                    sessione = _sess_multi[_kk]
                else:
                    sessione = nuova_sessione(opener, scelto.get("id") or "", modello, f"alluc-{a.tag}-{i}-{rip}")
                strumenti, testo, pensiero, eventi, dedup = un_turno(opener, sessione, domanda)
                err = ""
            except Exception as e:
                sessione = locals().get("sessione")
                strumenti, testo, pensiero, eventi, dedup, err = [], "", "", [], 0, f"{type(e).__name__}: {str(e)[:200]}"
                time.sleep(5)
            sec = time.time() - t0
            g = giudica(pop, strumenti, testo, pensiero)
            turno = {"caso": i, "rip": rip, "pop": pop, "domanda": domanda, "sessione": sessione,
                     "secondi": round(sec, 1), "strumenti": strumenti, "dedup": dedup, "eventi": eventi,
                     "errore": err, "testo": testo, "pensiero": pensiero,
                     "pensiero_caratteri": len(pensiero), "testo_caratteri": len(testo), **g}
            dati["turni"].append(turno)
            fj.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
            nota(f"[{n}/{totale}] rip {rip} {pop:8} {g['esito']:17} {sec:6.1f}s tool={','.join(strumenti) or '-'} "
                 f"num={g['numeri']} pens={len(pensiero)} {'T1' if g['type1'] else ''}{'T2' if g['type2'] else ''} "
                 f"| {domanda[:48]}" + (f" ERR {err}" if err else ""))

    # riepilogo
    T = dati["turni"]
    nota("RIEPILOGO")
    for pop in ("entita", "aperta", "calcolo", "negativa"):
        tt = [t for t in T if t["pop"] == pop]
        if not tt:
            continue
        conta = {}
        for t in tt:
            conta[t["esito"]] = conta.get(t["esito"], 0) + 1
        punti = sum(t["punti"] for t in tt)
        med = sorted(t["secondi"] for t in tt)[len(tt) // 2]
        nota(f"  {pop:8} n={len(tt)} {conta} punti={punti:+d} mediana={med:.0f}s "
             f"T1={sum(t['type1'] for t in tt)} T2={sum(t['type2'] for t in tt)}")
    nota(f"  totale punti {sum(t['punti'] for t in T):+d} su {len(T)} turni; dedup hits {sum(t['dedup'] for t in T)}")
    nota("SUITE COMPLETA")


if __name__ == "__main__":
    main()
