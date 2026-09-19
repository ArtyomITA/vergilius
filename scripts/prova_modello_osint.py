"""Il modello sceglie lo strumento giusto?

Tutto il resto e' gia' verificato (48 controlli in prova_osint.py). Qui si prova
l'unica cosa che manca: dato il catalogo dei dieci strumenti OSINT e una domanda
in italiano, **QwenPaw chiama quello che serve?**

Non si giudica la prosa della risposta — si giudica la scelta. Se sbaglia
strumento, nessuna qualita' di scrittura salva la risposta.

Uso:
    venv\\Scripts\\python.exe scripts\\prova_modello_osint.py [modello]
"""

import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, r"d:\assistenteeee\odysseus")

LLAMA = "http://127.0.0.1:8012/v1/chat/completions"
MODELLO = sys.argv[1] if len(sys.argv) > 1 else "qwenpaw"

# (domanda, strumenti accettabili, strumenti che sarebbero uno sbaglio grave)
CASI = [
    ("Cosa sta succedendo di importante nel mondo adesso?",
     {"osint_situazione"}, {"osint_recon", "osint_zona"}),
    ("Fammi una classifica di cosa sta succedendo di grave in questo momento.",
     {"osint_situazione"}, {"osint_recon"}),
    ("Quali sono le ultime notizie sull'Ucraina?",
     {"osint_notizie"}, {"osint_recon", "osint_militare"}),
    ("Che notizie ci sono nella zona del Mar Rosso negli ultimi due giorni?",
     {"osint_notizie", "osint_zona"}, {"osint_recon"}),
    ("Quali forze militari si stanno muovendo adesso?",
     {"osint_militare"}, {"osint_recon", "osint_notizie"}),
    ("Ci sono aerei cisterna in volo?",
     {"osint_militare"}, {"osint_recon", "osint_notizie"}),
    ("Quali sono gli allarmi piu' importanti attualmente?",
     {"osint_allerte"}, {"osint_recon"}),
    ("Cosa c'e' vicino a Odessa?",
     {"osint_zona"}, {"osint_recon"}),
    ("Dov'e' l'aereo con sigla RCH462?",
     {"osint_cerca"}, {"osint_recon", "osint_situazione"}),
    ("Chi c'e' dietro l'indirizzo IP 8.8.8.8?",
     {"osint_recon"}, {"osint_situazione", "osint_notizie"}),
    ("Centra la mappa su Kyiv.",
     {"osint_mappa"}, {"osint_zona", "osint_notizie"}),
    ("Mostrami sulla mappa solo i voli militari.",
     {"osint_mappa"}, {"osint_militare"}),
]

SISTEMA = (
    "Sei l'assistente di Vergilius e hai accesso a ShadowBroker, una piattaforma "
    "di intelligence geospaziale in tempo reale. Rispondi in italiano.\n"
    "Quando l'utente chiede informazioni sul mondo, chiama SEMPRE lo strumento "
    "adatto invece di rispondere a memoria: i tuoi dati di addestramento sono "
    "vecchi, gli strumenti sono aggiornati al minuto.\n"
)


def chiama(messaggi, strumenti, temperatura=0.2, timeout=300):
    corpo = {
        "model": MODELLO,
        "messages": messaggi,
        "tools": strumenti,
        "tool_choice": "auto",
        "temperature": temperatura,
        "max_tokens": 700,
    }
    req = urllib.request.Request(
        LLAMA, data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def strumenti_chiamati(risposta):
    try:
        msg = risposta["choices"][0]["message"]
    except (KeyError, IndexError):
        return [], ""
    chiamate = msg.get("tool_calls") or []
    nomi = []
    for c in chiamate:
        n = (c.get("function") or {}).get("name")
        if n:
            nomi.append(n)
    return nomi, (msg.get("content") or "").strip()


def main():
    from src.shadowbroker.schemi import OSINT_TOOL_SCHEMAS, REGOLE_OSINT

    sistema = SISTEMA + "\n" + REGOLE_OSINT
    print(f"modello: {MODELLO}")
    print(f"strumenti offerti: {len(OSINT_TOOL_SCHEMAS)}")
    print(f"prompt di sistema: ~{round(len(sistema)/3.6)} token\n")
    print("=" * 78)

    giusti = accettabili = sbagliati = nessuno = 0
    tempi = []
    for domanda, attesi, vietati in CASI:
        t0 = time.time()
        try:
            r = chiama([{"role": "system", "content": sistema},
                        {"role": "user", "content": domanda}],
                       OSINT_TOOL_SCHEMAS)
        except urllib.error.HTTPError as e:
            print(f" X  {domanda[:52]:<54} HTTP {e.code}")
            sbagliati += 1
            continue
        except Exception as e:
            print(f" X  {domanda[:52]:<54} {type(e).__name__}")
            sbagliati += 1
            continue
        dt = time.time() - t0
        tempi.append(dt)
        nomi, testo = strumenti_chiamati(r)

        if not nomi:
            segno, esito = "-", f"NESSUNO STRUMENTO — ha risposto a memoria: {testo[:44]}"
            nessuno += 1
        elif nomi[0] in attesi:
            segno, esito = " ", nomi[0]
            giusti += 1
        elif set(nomi) & vietati:
            segno, esito = "X", f"SBAGLIATO: {', '.join(nomi)}"
            sbagliati += 1
        else:
            segno, esito = "~", f"accettabile: {', '.join(nomi)}"
            accettabili += 1
        print(f" {segno}  {domanda[:52]:<54} {dt:>5.1f}s  {esito}")

    print("=" * 78)
    tot = len(CASI)
    print(f"  {giusti}/{tot} centrati, {accettabili} accettabili, "
          f"{sbagliati} sbagliati, {nessuno} senza strumento")
    if tempi:
        print(f"  tempo medio {sum(tempi)/len(tempi):.1f}s, massimo {max(tempi):.1f}s")

    # Secondo giro: il modello sa usare quello che riceve?
    print("\n" + "=" * 78)
    print("GIRO COMPLETO: domanda -> strumento -> risposta in italiano")
    print("=" * 78)
    from src.agent_tools import TOOL_HANDLERS
    import asyncio

    domanda = "Quali sono gli allarmi piu' importanti nel mondo adesso?"
    r = chiama([{"role": "system", "content": sistema},
                {"role": "user", "content": domanda}], OSINT_TOOL_SCHEMAS)
    nomi, _ = strumenti_chiamati(r)
    if not nomi:
        print("  il modello non ha chiamato nessuno strumento; giro interrotto")
        return 1
    chiamata = r["choices"][0]["message"]["tool_calls"][0]
    nome = chiamata["function"]["name"]
    args = chiamata["function"].get("arguments") or "{}"
    print(f"  1. ha scelto: {nome}({args[:70]})")

    esito = asyncio.run(TOOL_HANDLERS[nome](args, {}))
    uscita = esito.get("output") or esito.get("error") or ""
    print(f"  2. lo strumento ha reso {round(len(uscita)/3.6)} token")

    t0 = time.time()
    r2 = chiama([
        {"role": "system", "content": sistema},
        {"role": "user", "content": domanda},
        r["choices"][0]["message"],
        {"role": "tool", "tool_call_id": chiamata.get("id", "1"),
         "name": nome, "content": uscita},
    ], OSINT_TOOL_SCHEMAS)
    _, finale = strumenti_chiamati(r2)
    print(f"  3. risposta in {time.time()-t0:.1f}s, {len(finale)} caratteri:\n")
    print("     " + (finale[:1400].replace("\n", "\n     ") or "(vuota)"))
    return 0 if sbagliati == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
