"""Come si comporta il modello vero nel profilo Financial.

I briefing possono essere perfetti e l'orchestrazione comunque rotta: il punto
debole di un 9B non e' compilare gli argomenti, e' **scegliere lo strumento**.
Qui si misura proprio quello, su casistiche pensate per far sbagliare:

  * domande dirette          -> deve prendere lo strumento ovvio
  * domande ambigue          -> "difesa" e' un titolo o sono aerei militari?
  * domande incrociate       -> deve chiamarne due
  * domande fuori profilo    -> non deve inventarsi uno strumento che non ha
  * mappa                    -> deve evidenziare, MAI spegnere i livelli

Uso:  odysseus\\venv\\Scripts\\python.exe scripts\\prova_modello_finanza.py
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, "d:/assistenteeee/odysseus")
os.chdir("d:/assistenteeee/odysseus")

from src.shadowbroker.schemi import FINANCE_TOOL_SCHEMAS, OSINT_TOOL_SCHEMAS, REGOLE_FINANCE  # noqa: E402
from src.agent_tools.shadowbroker_tools import FINANCE_TOOL_NAMES  # noqa: E402

LLAMA = os.getenv("LLAMA_URL", "http://127.0.0.1:8012/v1/chat/completions")
MODELLO = os.getenv("LLAMA_MODEL", "qwenpaw")

SCHEMI = [s for s in (FINANCE_TOOL_SCHEMAS + OSINT_TOOL_SCHEMAS)
          if s["function"]["name"] in FINANCE_TOOL_NAMES]

SISTEMA = (
    "Sei un analista di rischio con accesso a strumenti di intelligence "
    "finanziaria. Rispondi chiamando lo strumento giusto.\n\n" + REGOLE_FINANCE
)

# (domanda, strumenti accettabili, strumenti da NON chiamare, nota)
CASI = [
    ("come vanno i titoli della difesa oggi?",
     {"fin_mercati"}, set(), "diretta"),

    ("che commesse militari sono state assegnate?",
     {"fin_appalti"}, set(), "diretta"),

    ("qualcuno dentro queste aziende sta vendendo azioni?",
     {"fin_insider"}, set(), "diretta"),

    ("come sta messa la difesa?",
     {"fin_mercati", "fin_appalti"}, set(),
     "AMBIGUA: 'difesa' puo' essere il comparto o i militari"),

    ("chi ha vinto i contratti piu' grossi e dove vengono eseguiti?",
     {"fin_appalti"}, set(), "chiede esplicitamente il luogo"),

    # «queste commesse» presuppone un turno precedente. Senza, la domanda e'
    # ambigua e misura la capacita' di indovinare, non l'orchestrazione: si
    # chiede quindi in modo autonomo, come farebbe un operatore al primo turno.
    ("prendi le commesse militari e mostrami sulla mappa dove vengono eseguite",
     {"osint_mappa"}, set(), "mappa, due passi"),

    ("ci sono notizie che spiegano il calo di Boeing?",
     {"osint_notizie", "fin_mercati"}, set(),
     "incrocio fra mercati e notizie"),

    ("qual e' il MSPR di Palantir?",
     {"fin_insider"}, set(), "termine tecnico"),

    ("che tempo fa a Milano?",
     set(), {"fin_mercati", "fin_appalti", "fin_insider"},
     "FUORI PROFILO: non deve forzare uno strumento finanziario"),

    ("nascondi tutto tranne i contratti",
     {"osint_mappa"}, set(),
     "TRAPPOLA: deve evidenziare, non spegnere i livelli"),

    # ── casi aggiunti dopo lo stallo osservato in chat (2 ago 2026) ──────
    # Il modello su questa domanda cerco' 'guerra conflitto' in italiano
    # (zero risultati), annuncio' un passo successivo e si fermo' senza
    # chiamare niente. La ricetta ora dice: fin_mercati PRIMA.
    ("rispetto alle ultime news di guerra, quali hanno influenzato i mercati?",
     {"fin_mercati"}, set(),
     "INCROCIO guerra×mercati: fin_mercati prima, non le news mondiali"),

    ("cosa e' successo a RTX nelle ultime due settimane?",
     {"fin_archivio"}, set(),
     "STORICO: domanda sul passato → archivio, non gli strumenti live"),

    ("confronta il sentiment degli insider di Lockheed con le notizie recenti",
     {"fin_insider"}, set(),
     "incrocio insider×notizie, due strumenti"),

    # Il caso esatto del bug del 2 ago: il modello metteva "Boeing" in
    # `luogo` (geocoder a vuoto → proteste in Svezia). Ora esiste `soggetto`
    # e la regola lo indica: la chiamata giusta e' osint_notizie o
    # fin_mercati, MAI la ricerca a vuoto.
    ("cercami news su Boeing in calo contro il trend di settore",
     {"osint_notizie", "fin_mercati"}, set(),
     "news su AZIENDA: soggetto, non luogo"),

    ("ultime notizie su OpenAI",
     {"osint_notizie"}, set(),
     "entita' fuori watchlist: soggetto + ripiego web automatico"),

    # ── osint_web (2 ago 2026): la via d'uscita quando i feed non sanno ──
    ("chi e' l'amministratore delegato di Raytheon?",
     {"osint_web"}, set(),
     "BACKGROUND: il wire non ha biografie → ricerca web dichiarata"),

    ("a quanto sta NVDA in questo momento?",
     {"fin_mercati"}, {"osint_web"},
     "GUARDIA: il numero vive nel tool, MAI negli snippet del web"),
]


def _un_giro(messaggi, timeout=240):
    corpo = {
        "model": MODELLO, "messages": messaggi, "tools": SCHEMI,
        "tool_choice": "auto", "temperature": 0.2, "max_tokens": 400,
    }
    req = urllib.request.Request(
        LLAMA, data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"})
    # Un 500 isolato da llama-server (contesto lungo al terzo giro, swap del
    # modello) non e' un errore di orchestrazione: un solo tentativo in piu'
    # distingue il server inciampato dal modello che sbaglia.
    for tentativo in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code >= 500 and tentativo == 1:
                time.sleep(3)
                continue
            raise
    return (d.get("choices") or [{}])[0].get("message") or {}


def _chiamate_di(msg):
    fuori = []
    for c in (msg.get("tool_calls") or []):
        f = c.get("function") or {}
        try:
            args = json.loads(f.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_grezzo": (f.get("arguments") or "")[:60]}
        fuori.append((f.get("name"), args))
    return fuori


def chiama(domanda, giri=2, timeout=240):
    """Fino a `giri` passaggi, eseguendo davvero gli strumenti.

    Un giro solo misura la cosa sbagliata sulle domande di mappa: prendere
    prima i dati e poi mostrarli e' la sequenza **giusta**, e uno scatto
    singolo la registra come «non ha chiamato la mappa». Qui il risultato dello
    strumento torna al modello, come nel ciclo vero dell'agente.
    """
    from src.agent_tools import TOOL_HANDLERS
    import asyncio

    messaggi = [{"role": "system", "content": SISTEMA},
                {"role": "user", "content": domanda}]
    tutte = []
    testo = ""
    t0 = time.time()

    for giro in range(giri):
        msg = _un_giro(messaggi, timeout=timeout)
        chiamate = _chiamate_di(msg)
        testo = (msg.get("content") or "").strip()
        tutte.extend(chiamate)
        if not chiamate:
            break
        messaggi.append({
            "role": "assistant", "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls") or [],
        })
        for c in (msg.get("tool_calls") or []):
            f = c.get("function") or {}
            nome = f.get("name")
            gestore = TOOL_HANDLERS.get(nome)
            if gestore is None:
                esito = json.dumps({"error": f"strumento {nome} inesistente"})
            else:
                try:
                    r = asyncio.run(gestore(f.get("arguments") or "{}", {}))
                    esito = str(r.get("output") or r.get("error") or "")[:3000]
                except Exception as e:
                    esito = f"errore: {type(e).__name__}: {e}"
            messaggi.append({"role": "tool", "tool_call_id": c.get("id") or nome,
                             "name": nome, "content": esito})

    return tutte, testo, time.time() - t0


def main():
    print(f"modello: {MODELLO} · {len(SCHEMI)} strumenti nel profilo\n")
    print(f"{'caso':52} {'esito':7} {'s':>5}  strumento scelto")
    print("-" * 108)

    ok = falliti = 0
    tempi = []
    problemi = []

    for domanda, attesi, vietati, nota in CASI:
        try:
            # Tre giri, non due: gli incroci veri (dati → secondo strumento →
            # risposta) hanno bisogno del terzo passaggio per chiudersi.
            chiamate, testo, secondi = chiama(domanda, giri=3)
        except Exception as e:
            print(f"{domanda[:52]:52} {'ERRORE':7}        {type(e).__name__}: {str(e)[:40]}")
            falliti += 1
            continue

        tempi.append(secondi)
        nomi = {n for n, _ in chiamate}

        if vietati and (nomi & vietati):
            esito, buono = "SBAGLIA", False
            problemi.append(f"«{domanda}» ha chiamato {nomi & vietati} e non doveva")
        elif not attesi:
            buono = not nomi
            esito = "ok" if buono else "SBAGLIA"
            if not buono:
                problemi.append(f"«{domanda}» doveva rispondere a parole, ha chiamato {nomi}")
        else:
            buono = bool(nomi & attesi)
            esito = "ok" if buono else "SBAGLIA"
            if not buono:
                problemi.append(f"«{domanda}» attesi {attesi}, chiamati {nomi or 'nessuno'}")

        ok += buono
        falliti += not buono
        dettaglio = ", ".join(
            f"{n}({','.join(f'{k}={v}' for k, v in list(a.items())[:2])})" if a else n
            for n, a in chiamate) or "— solo testo"
        print(f"{domanda[:52]:52} {esito:7} {secondi:5.1f}  {dettaglio[:46]}")

        # La trappola della mappa merita un controllo suo.
        for n, a in chiamate:
            if n == "osint_mappa" and str(a.get("azione", "")).lower() == "livelli":
                problemi.append(
                    f"«{domanda}» ha usato osint_mappa azione=livelli: spegne quello "
                    f"che l'operatore guarda, doveva usare evidenzia o preset")

    print("\n" + "=" * 108)
    print(f"{ok}/{len(CASI)} corretti · tempo medio {sum(tempi)/max(len(tempi),1):.1f}s")
    if problemi:
        print(f"\nDA SISTEMARE ({len(problemi)}):")
        for p in problemi:
            print(f"  · {p}")
    return 0 if not problemi else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
