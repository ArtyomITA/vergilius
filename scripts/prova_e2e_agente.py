r"""Prova END-TO-END del profilo Financial attraverso l'API vera di Odysseus.

Perche' esiste: la prova diretta (prova_modello_finanza.py) parlava con llama
con un prompt piccolo e faceva 13/13, mentre la chat vera si fermava dopo la
prima chiamata. Due ambienti diversi = il test misurava quello sbagliato.
Questa prova fa ESATTAMENTE il percorso di un turno dell'utente: login,
sessione, POST /api/chat in modalita' agente col profilo Financial, lettura
dello stream SSE. Se si blocca qui, si blocca anche nel browser — e viceversa.

Uso:  odysseus\venv\Scripts\python.exe scripts\prova_e2e_agente.py
Con ODYSSEUS_LLM_DUMP attivo sul server, ogni giro lascia il payload su disco.
"""

import json
import re
import sys
import time
import urllib.request
import http.cookiejar

BASE = "http://127.0.0.1:7000"
# utente e password, una per riga. Fuori dallo script apposta.
CREDENZIALI = r"d:\assistenteeee\scripts\.credenziali_odysseus"

# (domanda, minimo strumenti distinti attesi, minima lunghezza risposta)
CASI = [
    ("rispetto alle ultime news di guerra, quali hanno influenzato i mercati?", 2, 200),
    ("dammi il quadro generale con tutte le info finanziarie che hai di oggi", 2, 300),
    ("cercami news su Boeing in calo contro il trend di settore", 1, 200),
    # osint_web: background che il wire non ha — deve uscire sul web e dirlo.
    ("chi guida Lockheed Martin oggi e da quando?", 1, 100),
]

# La firma dello stallo: la risposta finisce annunciando un'azione.
ANNUNCIO = re.compile(
    r"(uso|chiamo|proviamo|adesso|ora)\s+(fin_|osint_|a\s+\w+are)[^.]*\.?\s*$",
    re.IGNORECASE)


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
    req = urllib.request.Request(
        BASE + percorso, data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _post_form(opener, percorso, campi, timeout=600):
    confine = "----provaE2E"
    parti = []
    for k, v in campi.items():
        parti.append(f"--{confine}\r\nContent-Disposition: form-data; "
                     f"name=\"{k}\"\r\n\r\n{v}\r\n")
    corpo = ("".join(parti) + f"--{confine}--\r\n").encode()
    req = urllib.request.Request(
        BASE + percorso, data=corpo,
        headers={"Content-Type": f"multipart/form-data; boundary={confine}"})
    return opener.open(req, timeout=timeout)


def un_turno(opener, sessione, domanda):
    """Manda la domanda e legge lo stream come farebbe il browser."""
    strumenti = []          # (nome) in ordine di esecuzione
    testo = []
    eventi_notevoli = []
    r = _post_form(opener, "/api/chat_stream", {
        "message": domanda,
        "session": sessione,
        "mode": "agent",
        "plan_mode": "false",
        "osint_mode": "true",
        "financial_mode": "true",
        "allow_bash": "false",
        "use_rag": "false",
        "allow_web_search": "false",
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
            strumenti.append(d.get("tool") or d.get("name") or "?")
        elif tipo in ("rounds_exhausted", "intent_nudge_exhausted",
                      "budget_exceeded"):
            eventi_notevoli.append(tipo)
        elif "delta" in d and not d.get("thinking"):
            testo.append(d.get("delta") or "")
    return strumenti, "".join(testo).strip(), eventi_notevoli


def main():
    opener = _client()
    utente, password = _leggi_credenziali()
    _post_json(opener, "/api/auth/login",
               {"username": utente, "password": password})

    # L'endpoint llama registrato nel DB: si prende il default, senza
    # chiedere niente all'utente e senza toccare chiavi.
    endpoints = _get_json(opener, "/api/model-endpoints")
    lista = endpoints if isinstance(endpoints, list) else (
        endpoints.get("endpoints") or endpoints.get("items") or [])
    scelto = None
    for e in lista:
        if isinstance(e, dict) and (e.get("is_default") or e.get("default")):
            scelto = e
            break
    if scelto is None and lista:
        scelto = lista[0]
    if not isinstance(scelto, dict):
        print(f"nessun endpoint modello trovato: {str(endpoints)[:300]}")
        sys.exit(2)
    modello = (scelto.get("default_model") or scelto.get("model")
               or scelto.get("model_name") or "ling")  # 27 ago: qwenpaw tolto da llama-swap (onda 5), fallback = modello di produzione

    with _post_form(opener, "/api/session", {
        "name": "prova-e2e",
        "endpoint_id": scelto.get("id") or "",
        "model": modello,
    }, timeout=60) as r:
        sess = json.loads(r.read().decode())
    sessione = sess.get("session_id") or sess.get("id") or sess.get("session")
    if not sessione:
        print(f"sessione non creata: {sess}")
        sys.exit(2)
    print(f"endpoint: {scelto.get('id', '?')[:8]} · modello: {str(modello)[:60]}\n")

    tutto_ok = True
    for domanda, minimo_tool, minima_lunghezza in CASI:
        t0 = time.time()
        try:
            strumenti, testo, note = un_turno(opener, sessione, domanda)
        except Exception as e:
            print(f"ERRORE {type(e).__name__}: {str(e)[:200]}\n  su: {domanda}")
            tutto_ok = False
            continue
        distinti = sorted(set(s for s in strumenti if s and s != "?"))
        stallo = bool(ANNUNCIO.search(testo[-160:])) if testo else True
        ok = (len(distinti) >= minimo_tool
              and len(testo) >= minima_lunghezza
              and not stallo)
        tutto_ok &= ok
        stato = "ok" if ok else "FALLITA"
        print(f"[{stato}] {time.time()-t0:6.1f}s  {domanda[:58]}")
        print(f"        strumenti ({len(strumenti)} chiamate, "
              f"{len(distinti)} distinti): {', '.join(strumenti) or 'NESSUNO'}")
        print(f"        risposta: {len(testo)} caratteri"
              + ("  <-- FINISCE CON UN ANNUNCIO" if stallo and testo else "")
              + (f"  note: {note}" if note else ""))
        if not ok and testo:
            print(f"        coda: …{testo[-180:]}")
        print()

    print("=" * 76)
    print("E2E: " + ("TUTTO OK" if tutto_ok else "FALLITA — il loop vero non regge"))
    sys.exit(0 if tutto_ok else 1)


if __name__ == "__main__":
    main()
