r"""Suite LUNGA end-to-end (19 set 2026): 4 scenari da 5 turni nella STESSA sessione, domande complesse
(piu' strumenti per turno, calcoli sulla storia, cambio di argomento, sintesi lunga, dato inesistente).
Serve a decidere quali vincoli dell'harness tenere con LFM: misura cio' che le suite corte non vedono
([state] dal 3o giro, nudge, nota delle tracce, regole di profilo, budget di pensiero su ricerche a passi).

Uso:  odysseus\venv\Scripts\python.exe scripts\suite-lunga-e2e.py --tag L1 [--scenari 1,2] [--turni 2] [--riprendi]
Stato: misure/onda4/lunga-TAG.txt (riga per riga), lunga-TAG.json (testi completi, incrementale).
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("alluc", str(Path(__file__).with_name("suite-allucinazioni-e2e.py")))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
OUT = A.OUT

# attesa: tool = deve chiamare; libero = puo' rispondere dalla storia; niente = non deve chiamare;
#         astieni = il dato non esiste, deve dirlo
SCENARI = {
    1: ("difesa", [
        ("tool", "Fammi il quadro di oggi sul settore difesa: prezzi e variazioni di Lockheed Martin, RTX, Northrop Grumman e General Dynamics, con le notizie che li muovono."),
        ("libero", "Quale dei quattro ha fatto meglio oggi e di quanti punti percentuali ha battuto il peggiore?"),
        ("tool", "Ci sono stati acquisti o vendite di insider su Lockheed Martin e RTX di recente? Cosa dice l'MSPR?"),
        ("tool", "E gli appalti recenti del Pentagono? Dimmi i tre più grossi con importo e azienda."),
        ("libero", "Mettendo insieme prezzi, insider e appalti visti finora, scrivimi un rapporto di una pagina con una tabella riassuntiva e i rischi. Solo dati che hai visto davvero."),
    ]),
    2: ("mondo-mercati", [
        ("tool", "Cosa sta succedendo di importante nel mondo oggi? Dammi i cinque fatti principali con le fonti."),
        ("tool", "Approfondisci il secondo fatto: leggi l'articolo e dimmi cosa dice davvero."),
        ("tool", "Questo ha mosso i mercati? Guarda le borse e le notizie finanziarie di oggi e dimmi se c'è un legame oppure no."),
        ("tool", "Ho 20.000 euro divisi a metà tra Apple e Nvidia: con le variazioni percentuali di oggi, quanto ho guadagnato o perso in euro?"),
        ("libero", "Riassumi tutta la conversazione in dieci righe, solo con dati che hai visto davvero."),
    ]),
    3: ("sette-titoli", [
        ("tool", "Confronta Apple, Microsoft, Nvidia, Alphabet e Amazon: prezzo, variazione di oggi e una notizia per ciascuna. Poi dimmi quale sceglieresti guardando solo questi dati, e perché."),
        ("tool", "Aggiungi Tesla e Meta al confronto e rifai la classifica per variazione di oggi."),
        ("libero", "Quanto costerebbe comprare 3 azioni di ciascuno dei sette titoli? Totale in dollari e in euro con un cambio di 0,92."),
        ("niente", "Cos'è il rapporto P/E, in parole semplici?"),
        ("tool", "Torniamo ai sette titoli: quale ha la notizia più negativa e cosa dice esattamente?"),
    ]),
    4: ("italia-passato", [
        ("tool", "Come sono andate Leonardo, Unicredit ed Eni in borsa oggi?"),
        ("tool", "Chi è l'amministratore delegato di Unicredit e da quando?"),
        ("tool", "Rispetto a due settimane fa, come sono cambiati i mercati? Usa l'archivio."),
        ("astieni", "Qual è il dividendo per azione che Eni pagherà nel 2028?"),
        ("libero", "Fammi un grafico a barre con le variazioni di oggi dei titoli di cui abbiamo parlato in questa chat."),
    ]),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--scenari", default="1,2,3,4")
    ap.add_argument("--turni", type=int, default=5, help="turni per scenario (2 = prova a secco)")
    ap.add_argument("--riprendi", action="store_true")
    a = ap.parse_args()
    fj, ft = OUT / f"lunga-{a.tag}.json", OUT / f"lunga-{a.tag}.txt"
    dati = json.loads(fj.read_text(encoding="utf-8")) if (a.riprendi and fj.exists()) else {"tag": a.tag, "turni": [], "sessioni": {}}
    fatti = {(t["scenario"], t["turno"]) for t in dati["turni"]}

    def nota(msg):
        riga = f"{time.strftime('%H:%M:%S')} gpu[{A.gpu()}] {msg}"
        print(riga, flush=True)
        with open(ft, "a", encoding="utf-8") as f:
            f.write(riga + "\n")

    opener = A._client()
    utente, password = A._leggi_credenziali()
    A._post_json(opener, "/api/auth/login", {"username": utente, "password": password})
    endpoints = A._get_json(opener, "/api/model-endpoints")
    lista = endpoints if isinstance(endpoints, list) else (endpoints.get("endpoints") or endpoints.get("items") or [])
    scelto = next((e for e in lista if isinstance(e, dict) and (e.get("is_default") or e.get("default"))), None) or lista[0]
    modello = scelto.get("default_model") or scelto.get("model") or "ling"
    scen = [int(x) for x in a.scenari.split(",") if x.strip()]
    totale = len(scen) * a.turni
    nota(f"suite lunga {a.tag}: scenari {scen} x {a.turni} turni = {totale}, gia' fatti {len(fatti)}, modello {modello}")
    n = 0
    for s in scen:
        nome, turni = SCENARI[s]
        for k, (attesa, domanda) in enumerate(turni[:a.turni], 1):
            n += 1
            if (s, k) in fatti:
                continue
            sessione = dati["sessioni"].get(str(s))
            t0 = time.time()
            try:
                if not sessione:
                    sessione = A.nuova_sessione(opener, scelto.get("id") or "", modello, f"lunga-{a.tag}-{nome}")
                    dati["sessioni"][str(s)] = sessione
                strumenti, testo, pensiero, eventi, _ = A.un_turno(opener, sessione, domanda)
                err = ""
            except Exception as e:
                strumenti, testo, pensiero, eventi, err = [], "", "", [], f"{type(e).__name__}: {str(e)[:200]}"
                time.sleep(5)
            sec = time.time() - t0
            astiene = bool(A.ASTENSIONE_RE.search(testo))
            if attesa == "tool":
                esito = "ok" if strumenti else ("astiene" if astiene else "SENZA-TOOL")
            elif attesa == "niente":
                esito = "TOOL-INUTILE" if strumenti else "ok"
            elif attesa == "astieni":
                esito = "ok" if (astiene or "non" in testo.lower()[:400]) else "DA-LEGGERE"
            else:
                esito = "ok" if testo else "VUOTA"
            if not testo and not err:
                esito = "VUOTA"
            dati["turni"].append({"scenario": s, "nome": nome, "turno": k, "attesa": attesa, "domanda": domanda,
                                  "sessione": sessione, "secondi": round(sec, 1), "strumenti": strumenti,
                                  "eventi": eventi, "errore": err, "esito": esito, "astiene": astiene,
                                  "testo": testo, "pensiero": pensiero,
                                  "pensiero_caratteri": len(pensiero), "testo_caratteri": len(testo)})
            fj.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
            nota(f"[{n}/{totale}] S{s}.{k} {attesa:7} {esito:12} {sec:6.1f}s tool={len(strumenti)}:{','.join(strumenti) or '-'} "
                 f"pens={len(pensiero)} testo={len(testo)} ev={','.join(eventi) or '-'}" + (f" ERR {err}" if err else ""))
    T = dati["turni"]
    sec = sorted(t["secondi"] for t in T) or [0]
    nota(f"RIEPILOGO turni={len(T)} mediana={sec[len(sec)//2]:.0f}s max={sec[-1]:.0f}s totale={sum(sec)/60:.1f}min "
         f"chiamate={sum(len(t['strumenti']) for t in T)} non-ok={[(t['scenario'], t['turno'], t['esito']) for t in T if t['esito'] != 'ok']}")
    nota("SUITE COMPLETA")


if __name__ == "__main__":
    main()
