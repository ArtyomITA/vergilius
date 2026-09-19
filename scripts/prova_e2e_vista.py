r"""Prova END-TO-END della modalita' Vista attraverso l'API vera di Odysseus.

Percorso identico a un utente: login, POST /api/vista/avvia (il loader: Holo
parte e si scalda), sessione, turni con vista_mode=true, lettura dello stream.
Gli occhi guardano lo schermo REALE; il banco fa solo domande (niente click):
verifica che il loop passi dal convertitore nativo (TOOL_TAGS), che il tool
vista_* venga eseguito davvero e che la risposta racconti cio' che Holo vede.

Uso:  odysseus\venv\Scripts\python.exe scripts\prova_e2e_vista.py
"""

import json
import os
import re
import sys
import time
import urllib.request
import http.cookiejar

sys.path.insert(0, os.path.dirname(__file__))
from prova_e2e_agente import _client, _leggi_credenziali, _get_json, _post_json, _post_form, BASE, ANNUNCIO  # noqa: E402

# (domanda, tool attesi (almeno uno), minima lunghezza risposta)
CASI = [
    ("Cosa vedi sullo schermo in questo momento?", {"vista_schermo"}, 60),
    ("C'e' qualche finestra di dialogo o popup aperto?", {"vista_schermo"}, 20),
    # Il 3o puo' rispondere dal turno precedente senza riguardare: accettato
    # (set vuoto = nessun tool richiesto). Misurato: "Chrome." in 11s.
    ("Che applicazione e' in primo piano? Rispondi in una riga.", set(), 3),
    ("Guarda di nuovo lo schermo: cosa e' cambiato rispetto a prima?", {"vista_schermo"}, 20),
]


def un_turno(opener, sessione, domanda):
    strumenti, testo, note = [], [], []
    r = _post_form(opener, "/api/chat_stream", {
        "message": domanda, "session": sessione, "mode": "agent", "plan_mode": "false",
        "vista_mode": "true", "allow_bash": "false", "use_rag": "false", "allow_web_search": "false",
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
        elif tipo in ("rounds_exhausted", "intent_nudge_exhausted", "budget_exceeded"):
            note.append(tipo)
        elif "delta" in d and not d.get("thinking"):
            testo.append(d.get("delta") or "")
    return strumenti, "".join(testo).strip(), note


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    opener = _client()
    utente, password = _leggi_credenziali()
    _post_json(opener, "/api/auth/login", {"username": utente, "password": password})

    # Il loader: come il click sul toggle Vista.
    t0 = time.time()
    req = urllib.request.Request(BASE + "/api/vista/avvia", data=b"", method="POST")
    with opener.open(req, timeout=400) as r:
        stato = json.loads(r.read().decode())
    print(f"vista avviata in {time.time()-t0:.1f}s: {stato}\n")

    endpoints = _get_json(opener, "/api/model-endpoints")
    lista = endpoints if isinstance(endpoints, list) else (endpoints.get("endpoints") or endpoints.get("items") or [])
    scelto = next((e for e in lista if isinstance(e, dict) and (e.get("is_default") or e.get("default"))), None) or (lista[0] if lista else None)
    modello = (scelto.get("default_model") or scelto.get("model") or scelto.get("model_name") or "ling")
    with _post_form(opener, "/api/session", {"name": "prova-e2e-vista", "endpoint_id": scelto.get("id") or "", "model": modello}, timeout=60) as r:
        sess = json.loads(r.read().decode())
    sessione = sess.get("session_id") or sess.get("id") or sess.get("session")
    print(f"endpoint: {scelto.get('id','?')[:8]} · modello: {modello}\n")

    tutto_ok = True
    for domanda, attesi, minima in CASI:
        t0 = time.time()
        try:
            strumenti, testo, note = un_turno(opener, sessione, domanda)
        except Exception as e:
            print(f"ERRORE {type(e).__name__}: {str(e)[:200]}\n  su: {domanda}"); tutto_ok = False; continue
        distinti = set(s for s in strumenti if s and s != "?")
        stallo = bool(ANNUNCIO.search(testo[-160:])) if testo else True
        ok = (not attesi or bool(distinti & attesi)) and len(testo) >= minima and not stallo
        tutto_ok &= ok
        print(f"[{'ok' if ok else 'FALLITA'}] {time.time()-t0:6.1f}s  {domanda[:58]}")
        print(f"        strumenti: {', '.join(strumenti) or 'NESSUNO'}" + (f"  note: {note}" if note else ""))
        print(f"        risposta ({len(testo)} car): {testo[:300].replace(chr(10), ' | ')}")
        print()
    print("=" * 76)
    print("E2E VISTA: " + ("TUTTO OK" if tutto_ok else "FALLITA — il loop vero non regge"))
    sys.exit(0 if tutto_ok else 1)


if __name__ == "__main__":
    main()
