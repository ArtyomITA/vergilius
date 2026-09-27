r"""Prove offline dei cancelli 2 e 3 della biblioteca di skill e dell'installatore (stanza 3, 27 set 2026).

Nessuna rete, nessuna GPU, nessun servizio, mai odysseus\data: server e stream SSE finti, cartelle temporanee.
  selettore     banco-selettore-skill.py dal vivo contro un llama-swap FINTO (probabilita' inventate da un oracolo):
                registro jsonl, metriche, verdetto, --riprendi, rifiuto di una ripresa con parametri cambiati;
                registro incompleto (troncato o con richieste fallite non consecutive) = INCOMPLETO, mai un verdetto;
                divisione taratura/verifica stabile (mappa_oro, messaggi nuovi, storico dei banchi); oro dal messaggio;
  famiglia      banco-browser.py --ab-famiglia con tracce SSE finte: verdetto TIENI con un turno peggiorato (referto
                con le skill iniettate), arresto se il selettore e' spento, se il braccio A non ha l'evento, se il
                selettore non ha candidati o e' MUTO (nessuna decisione, tetto); NON VALIDO se B non inietta mai;
                --riprendi; regressione di --ab e --contaminazione;
  installatore  installa-biblioteca.py --prova-famiglia / --togli-prova su una DATA temporanea (--dest):
                copia, manifesto, prova gia' in corso, conflitti, skill gia' presente identica, cancello 1 fallito,
                skill riscritta durante la prova (resta), operazioni di verifica del dominio giusto.

Uso: odysseus\venv\Scripts\python.exe scripts\prova-banchi-skill-offline.py [--parte selettore|famiglia|installatore|tutte]
"tutte" fa girare ogni parte in un processo a se', una dopo l'altra (un processo pesante alla volta).
"""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

QUI = Path(__file__).resolve().parent
RADICE = QUI.parent
BIBLIOTECA = RADICE / "biblioteca-skill"
FALLITE = []


def controlla(cond, msg):
    print(("  ok    " if cond else "  NO    ") + msg, flush=True)
    if not cond:
        FALLITE.append(msg)


def modulo(nome_file, nome):
    spec = importlib.util.spec_from_file_location(nome, QUI / nome_file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def esci_con(fn, *a, **k):
    """(codice di uscita, stdout) di una funzione che puo' chiamare sys.exit."""
    buf = io.StringIO()
    codice = 0
    with contextlib.redirect_stdout(buf):
        try:
            r = fn(*a, **k)
            codice = r if isinstance(r, int) else 0
        except SystemExit as e:
            codice = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            if e.code is not None and not isinstance(e.code, int):
                print(e.code)
    return codice, buf.getvalue()


# ------------------------------------------------------------------ parte 1: banco del selettore
def parte_selettore(tmp: Path):
    print("== banco-selettore-skill.py contro un llama-swap finto")
    B = modulo("banco-selettore-skill.py", "banco_selettore")
    voci, _info = B.carica_dataset(QUI / "banco-selettore-browser.json")
    B.dividi(voci)
    n_voci = len(voci)
    n_ver = sum(v["meta"] == "verifica" for v in voci)
    oro_di = {re.sub(r"\s+", " ", v["testo"]).strip(): v["oro"] for v in voci}
    testi_c20 = {re.sub(r"\s+", " ", v["testo"]).strip() for v in voci if v["gruppo"] == "C20"}
    skills, _ = B.carica_skill([BIBLIOTECA / "browser"], "admin")
    per_desc = {B.S1._pulisci_messaggio(s["description"], 240): s["name"] for s in skills}

    class ServerFinto:
        chiamate = []
        guasti = set()  # numeri delle richieste sullo slot del banco che falliscono (errore HTTP finto)

        def __init__(self, base, modello, reg):
            self.base, self.modello, self.reg = base, modello, reg
            self.slot0 = False

        def running(self):
            return {"running": [{"model": "lfm", "state": "ready"}]}

        def props(self):
            return {"total_slots": 4, "build_info": "finto"}

        def applica_template(self, msgs):
            return {"prompt": "<|startoftext|><|im_start|>system\n" + msgs[0]["content"] + "<|im_end|>\n"
                              "<|im_start|>user\n" + msgs[1]["content"] + "<|im_end|>\n<|im_start|>assistant\n<think>"}

        def tokenizza(self, testo):
            return {"tokens": [1, 6] + [9] * 300}

        def svuota(self, slot):
            if slot == 0:
                self.slot0 = False
            return {}

        def chat(self, payload, timeout=900.0):
            return {}, 0.1

        def completion(self, payload, timeout=120.0):
            if payload.get("id_slot") == 0:
                self.slot0 = True
                return {"tokens_evaluated": 8190}, 3.9
            ServerFinto.chiamate.append(payload["id_slot"])
            if len(ServerFinto.chiamate) in ServerFinto.guasti:
                raise RuntimeError("HTTP 503 finto")
            p = payload["prompt"]
            msg = re.search(r'Messaggio dell\'utente: "(.*)"', p).group(1)
            lettere = dict(re.findall(r"^([A-I])\. (.*)$", p, re.M))
            nome = {L: ("nessuna" if t.startswith("nessuna:") else per_desc[t]) for L, t in lettere.items()}
            oro = oro_di.get(msg, [])
            if not oro:
                # errore voluto e fisso: sulle due formulazioni di C20 (pagina d'errore, verifica) inietta la skill
                # dei muri. 2 su 22 casi "nessuna" di verifica = 9%, sotto il 10% del criterio (controllato sotto).
                sbaglia = msg in testi_c20
                punti = {L: (0.9 if n == ("sito-bloccato-cambia-fonte" if sbaglia else "nessuna") else 0.1 / 3)
                         for L, n in nome.items()}
            elif len(oro) == 1:
                punti = {L: (0.86 if n == oro[0] else 0.14 / 3) for L, n in nome.items()}
            else:
                punti = {L: (0.5 if n == oro[0] else 0.42 if n == oro[1] else 0.04) for L, n in nome.items()}
            top = [{"token": (" " + L if i % 2 else L), "logprob": math.log(v)}
                   for i, (L, v) in enumerate(sorted(punti.items(), key=lambda kv: -kv[1]))]
            top.append({"token": "Hello", "logprob": math.log(0.01)})
            lat = 0.31 if self.slot0 else 0.24
            return ({"completion_probabilities": [{"top_logprobs": top}], "tokens_evaluated": 311,
                     "tokens_cached": 0, "timings": {"prompt_ms": lat * 900}, "content": top[0]["token"],
                     "id_slot": payload["id_slot"]}, lat)

    B.crea_server = lambda base, modello, reg: ServerFinto(base, modello, reg)
    out = tmp / "selettore"
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--out", str(out), "--tag", "finto"])
    controlla(codice == 0, f"banco finto completo (uscita {codice})")
    jsonl = sorted(out.glob("selettore-browser-finto-*.jsonl"))[-1]
    righe = [json.loads(r) for r in jsonl.read_text(encoding="utf-8").splitlines() if r.strip()]
    risp = [r for r in righe if r["tipo"] == "risposta"]
    controlla(len(risp) == n_voci * 2 * 2, f"{len(risp)} risposte registrate ({n_voci} voci x 2 bracci x 2 passate)")
    controlla(all(s == 2 for s in ServerFinto.chiamate), "tutte le decisioni sullo slot 2")
    controlla(sum(r["tipo"] == "j" for r in righe) == n_voci, "braccio J registrato per ogni voce")
    controlla(any(r["tipo"] == "chat8k" for r in righe), "chat finta caricata nello slot 0 per la passata chat8k")
    testa = next(r for r in righe if r["tipo"] == "intestazione")
    controlla(len(testa["attese"]["ids"]) == n_voci and testa["attese"]["passate"] == ["vuoto", "chat8k"]
              and len(testa["meta_per_id"]) == n_voci, "intestazione con risposte attese e meta' di ogni voce")
    rie = json.loads(jsonl.with_name(jsonl.stem + "-riepilogo.json").read_text(encoding="utf-8"))
    controlla(rie["completezza"]["completo"] and rie["completezza"]["mancanti"] == 0, "registro completo")
    controlla(rie["passata_principale"] == "chat8k", "passata principale chat8k")
    vs = rie["verdetto"]["S"]
    controlla(vs["esito"] == "ACCENDI", f"verdetto S con l'oracolo buono: {vs['esito']} {vs['falliti']}")
    m = rie["bracci"]["S"]["regole"]["verifica"]["produzione"]
    controlla(m["n"] == n_ver and m["iniezioni_su_nessuna"] >= 1, f"verifica: {m['n']} voci, iniezioni su 'nessuna' "
              f"{m['iniezioni_su_nessuna']} su {m['casi_nessuna']} (l'oracolo ne sbaglia qualcuna apposta)")
    controlla(m["per_classe"]["due"]["esatte"] > 0, "voci con due skill: la regola 0,8 prende entrambe (0,5 + 0,42)")
    r1 = rie["bracci"]["S"]["regole"]["verifica"]["r1"]
    controlla(r1["per_classe"]["due"]["esatte"] == 0, "r1 non prende mai due skill")
    controlla("0.95" in rie["bracci"]["S"]["soglie_taratura"], "tabella delle soglie sulla taratura")

    # registro troncato (banco fermato da "tre errori di fila" dopo 30 risposte chat8k): nessun verdetto
    tenute, n_chat = [], 0
    for r in righe:
        if r["tipo"] == "risposta" and r["passata"] == "chat8k":
            n_chat += 1
            if n_chat > 30:
                continue
        tenute.append(r)
    parziale = tmp / "parziale" / "selettore-browser-parziale.jsonl"
    parziale.parent.mkdir(parents=True, exist_ok=True)
    parziale.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tenute), encoding="utf-8")
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--riepiloga", str(parziale)])
    rp = json.loads(parziale.with_name(parziale.stem + "-riepilogo.json").read_text(encoding="utf-8"))
    controlla(codice != 0 and "REGISTRO INCOMPLETO" in testo and "ACCENDI con" not in testo
              and all(v["esito"] == "INCOMPLETO" for v in rp["verdetto"].values())
              and rp["consiglio"].startswith("INCOMPLETO"),
              f"registro troncato: INCOMPLETO, uscita {codice}, nessun ACCENDI")
    controlla(rp["passata_principale"] == "vuoto" and rp["completezza"]["mancanti"] == n_voci * 2 * 2 // 2 - 30,
              f"passata principale = quella completa (vuoto), mancanti {rp['completezza']['mancanti']}")

    # richieste fallite NON consecutive: il banco arriva in fondo ma il registro resta incompleto; --riprendi completa
    ServerFinto.chiamate, ServerFinto.guasti = [], {40, 90, 150}
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--out", str(out), "--tag", "guasti"])
    jg = sorted(out.glob("selettore-browser-guasti-*.jsonl"))[-1]
    rg = json.loads(jg.with_name(jg.stem + "-riepilogo.json").read_text(encoding="utf-8"))
    controlla(codice == 1 and rg["completezza"]["mancanti"] == 3 and rg["completezza"]["errori_registrati"] == 3
              and rg["verdetto"]["S"]["esito"] == "INCOMPLETO" and "richieste fallite in questa sessione: 3" in testo,
              f"3 richieste fallite sparse: INCOMPLETO (uscita {codice}, mancanti {rg['completezza']['mancanti']})")
    ServerFinto.chiamate, ServerFinto.guasti = [], set()
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--out", str(out), "--riprendi", str(jg)])
    rg = json.loads(jg.with_name(jg.stem + "-riepilogo.json").read_text(encoding="utf-8"))
    controlla(codice == 0 and rg["completezza"]["completo"] and rg["verdetto"]["S"]["esito"] == "ACCENDI"
              and len(ServerFinto.chiamate) == 3 + 1,
              f"--riprendi rifa' solo le 3 fallite (+1 riscaldamento, la passata chat8k era completa): "
              f"{len(ServerFinto.chiamate)} richieste, {rg['verdetto']['S']['esito']}")

    # ripresa: meta' delle risposte cancellate (una si' e una no), il banco rifa' solo quelle
    tenute, tolte, visti = [], 0, 0
    for r in righe:
        if r["tipo"] == "risposta":
            visti += 1
            if visti % 2:  # una si' e una no: restano incomplete tutte e due le passate
                tolte += 1
                continue
        tenute.append(r)
    jsonl.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in tenute), encoding="utf-8")
    ServerFinto.chiamate = []
    codice, _ = esci_con(B.main, ["--famiglia", "browser", "--out", str(out), "--riprendi", str(jsonl)])
    nuove = len(ServerFinto.chiamate)
    controlla(codice == 0 and nuove == tolte + 2, f"--riprendi rifa' {nuove} richieste ({tolte} mancanti + 2 riscaldamenti)")
    righe2 = [json.loads(r) for r in jsonl.read_text(encoding="utf-8").splitlines() if r.strip()]
    controlla(sum(r["tipo"] == "risposta" for r in righe2) == len(risp), "dopo la ripresa il registro e' completo")
    controlla(sum(r["tipo"] == "j" for r in righe2) == n_voci, "la ripresa non duplica il braccio J")
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--out", str(out), "--riprendi", str(jsonl),
                                      "--soglia", "0.6"])
    controlla(codice != 0 and "banco nuovo" in testo, "ripresa con soglia diversa rifiutata")
    codice, _ = esci_con(B.main, ["--famiglia", "browser", "--riepiloga", str(jsonl)])
    controlla(codice == 0, "--riepiloga offline")
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--slot", "3", "--dry-run"])
    controlla(codice != 0 and "vietati" in testo, "slot 3 rifiutato")
    codice, testo = esci_con(B.main, ["--famiglia", "browser", "--modello", "lfm-uncensored", "--dry-run"])
    controlla(codice != 0 and "vietato" in testo, "lfm-uncensored rifiutato")
    parte_dataset(B, tmp)


def parte_dataset(B, tmp: Path):
    """Divisione stabile (niente fughe fra taratura e verifica) e oro dal solo messaggio: funzioni pure, niente rete."""
    print("== dataset del cancello 2: divisione stabile e oro dal messaggio")
    voci, info = B.carica_dataset(QUI / "banco-selettore-browser.json")
    B.dividi(voci)
    base = {v["id"]: v["meta"] for v in voci}
    # una skill nuova = una riga in mappa_oro: cambiano le classi, non la divisione
    vv = copy.deepcopy(voci)
    mappa = dict(info["mappa_oro"], paginazione="pagina-dopo-pagina", navigazione="naviga-pagina")
    for v in vv:
        v["oro"] = sorted({mappa[e] for e in v["etichette"] if e in mappa})
        v["classe"] = B.classe(v["oro"])
    B.dividi(vv)
    controlla({v["id"]: v["meta"] for v in vv} == base, "righe nuove in mappa_oro: nessuna voce cambia meta'")
    vv = copy.deepcopy(voci) + [{"id": f"M9{i}", "gruppo": f"M9{i}", "testo": "x", "etichette": ["chiacchiera"],
                                 "origine": "scritto", "ruolo_op": None, "meta_json": None, "oro": [],
                                 "classe": "nessuna"} for i in range(5)]
    B.dividi(vv)
    controlla(all(v["meta"] == base[v["id"]] for v in vv if v["id"] in base)
              and all(v["meta"] == B.meta_da_hash(v["gruppo"]) for v in vv if v["id"] not in base),
              "messaggi nuovi: meta' dall'hash del loro id, le voci vecchie non si spostano")
    controlla(all(v["meta"] == v["meta_json"] for v in voci if v.get("meta_json")),
              "messaggi M01-M53: meta' dal campo congelato del dataset")
    # storico: un banco gia' registrato con M04 in verifica -> la divisione di oggi e' una fuga
    sto = tmp / "storico"
    sto.mkdir(parents=True, exist_ok=True)
    (sto / "selettore-browser-vecchio.jsonl").write_text(
        json.dumps({"tipo": "intestazione", "meta_per_id": dict(base, M04="verifica")}) + "\n", encoding="utf-8")
    err = B.storico_divisione(sto, "browser", voci)
    controlla(len(err) == 1 and "M04 verifica->taratura" in err[0], "voce spostata rispetto a un banco vecchio: errore")
    (sto / "selettore-browser-vecchio.jsonl").write_text(
        json.dumps({"tipo": "intestazione", "meta_per_id": base}) + "\n", encoding="utf-8")
    controlla(not B.storico_divisione(sto, "browser", voci), "stessa divisione del banco vecchio: nessun errore")
    # oro dal solo messaggio: formulazioni di forma uguale hanno lo stesso oro, le non decidibili sono fuori
    per_id = {v["id"]: v for v in voci}
    fuori = ("C05-a", "C09-d", "C09-a", "C10-d", "C10-a", "C13-a", "C22-d", "C22-a", "M43")
    controlla(not any(i in per_id for i in fuori) and set(info["escluse"]) == set(fuori),
              "voci con oro non decidibile dal messaggio escluse (con motivo)")
    due = ["articolo-lungo-trova-dato", "cerca-nel-sito"]
    controlla(per_id["A08-a"]["oro"] == per_id["M22"]["oro"] == per_id["C05-d"]["oro"] == per_id["M25"]["oro"] == due,
              "ricerca nel sito + dato nella pagina = due skill (A08, C05-d, M22, M25)")
    controlla(per_id["A03-d"]["oro"] == per_id["A04-d"]["oro"] == per_id["M07"]["oro"] == ["articolo-lungo-trova-dato"]
              and per_id["C02-a"]["oro"] == per_id["C03-a"]["oro"] == per_id["M02"]["oro"],
              "dato in una voce o in una tabella = articolo-lungo (A03, C02 come A04, C03, M02, M07)")
    controlla(per_id["C05-d"]["etichette_op"] == ["modulo-ricerca"], "skill_attese delle operazioni intatte (cancello 3)")
    c = Counter(v["classe"] for v in voci)
    controlla(len(voci) >= 120 and c["nessuna"] / len(voci) >= 0.25 and c["due"] / len(voci) >= 0.10,
              f"proporzioni: {len(voci)} voci, nessuna {c['nessuna']}, due {c['due']}")
    # refusi nelle chiavi di oro_messaggio / escluse: errori, mai ignorati
    dati = json.loads((QUI / "banco-selettore-browser.json").read_text(encoding="utf-8"))
    dati["operazioni"] = str(QUI / "operazioni-browser.json")
    dati["oro_messaggio"]["A99-d"] = ["tabella"]
    dati["escluse"]["Z01"] = "refuso"
    dati["escluse"]["A01"] = ""
    finto = tmp / "dataset-refusi.json"
    finto.write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    _, info_r = B.carica_dataset(finto)
    controlla(len(info_r["problemi"]) == 3, f"chiavi sbagliate in oro_messaggio/escluse e motivo vuoto: {info_r['problemi']}")


# ------------------------------------------------------------------ parte 2: A-B-B-A per famiglia
RISPOSTE_OK = {
    "A05": "San Marino ha 31477 abitanti secondo la pagina.",
    "C03": "L'ottavo presidente e' Francesco Cossiga.",
    "C04": "Nel 2008 i Boston Bruins hanno 53 vittorie.",
    "C05": "La parola l'ha coniata Horace Walpole nel 1754.",
    "C11": "Ha piu' abitanti Andorra: 52523 in piu' di San Marino.",
    "C18": "La pagina chiede un captcha: non posso andare avanti da solo.",
    "C22": "Il Presidente della Repubblica e' Sergio Mattarella.",
    "V01": "Nel Cinquecento furono 30 le edizioni.",
    "V02": "Si', c'e' La Divina Commedia di Dante.",
    "V03": "C'e' un muro a pagamento: non posso leggerlo senza abbonamento, cerco un'altra fonte.",
    "V04": "Serve il login con le tue credenziali: non accedo al tuo account.",
    "V05": "C'e' un captcha: non posso inviare il modulo.",
    "N02": "URL significa Uniform Resource Locator.",
    "C09": "Nel 2015 il miglior film e' Spotlight.",
    "C10": "La categoria Poetry contiene 19 libri.",
    "C20": "La voce non esiste su Wikipedia (404).",
}
STATO = {"C18": "blocked: captcha", "V05": "blocked: captcha", "V03": "cookie_banner: left_open (rejecting needs a paid subscription)",
         "V04": "blocked: login"}


def parte_famiglia(tmp: Path):
    print("== banco-browser.py --ab-famiglia con tracce SSE finte")
    BB = modulo("banco-browser.py", "banco_browser")
    ops = json.loads((QUI / "operazioni-browser.json").read_text(encoding="utf-8"))["operazioni"]
    per_domanda = {o["domanda"]: o for o in ops}
    mappa = BB.mappa_oro(QUI / "banco-selettore-browser.json")
    stato = {"scenario": "tieni", "turni": 0}

    def evento_skill(campi, op, braccio, blocco):
        sc = stato["scenario"]
        if braccio == "A":
            if sc == "a_senza_evento":
                return None
            if "bench_skills" in campi and campi["bench_skills"] == "nessuna":
                return {"skills": [], "ids": [], "origine": "banco", "p": [], "candidati": 0, "ms": 0, "motivo": "nessuna"}
            return None
        if sc == "classico":
            nomi = [x for x in re.split(r"[,;\s]+", campi.get("bench_skills", "")) if x and x != "nessuna"]
            return {"skills": nomi, "origine": "banco", "p": [1.0] * len(nomi), "candidati": len(nomi), "motivo": ""}
        if "bench_skills" in campi or sc == "leva_spenta":
            return None
        if sc == "senza_candidati":
            return {"skills": [], "origine": "selettore", "p": [], "candidati": 0, "ms": 3, "motivo": "nessun candidato"}
        if sc in ("muto_nessuna decisione", "muto_tetto"):  # selettore acceso che non decide mai
            return {"skills": [], "origine": "selettore", "p": [], "candidati": 3, "ms": 800, "motivo": sc[5:]}
        if sc == "regola_sempre":  # decide sempre "nessuna": B identico ad A
            return {"skills": [], "origine": "selettore", "p": [], "candidati": 3, "ms": 280, "motivo": "regola"}
        if op["id"] == "N02" and blocco == 2:  # un tetto isolato: avviso, non arresto
            return {"skills": [], "origine": "selettore", "p": [], "candidati": 3, "ms": 800, "motivo": "tetto"}
        oro = BB.oro_di(op, mappa)
        if op["id"] == "C10" and blocco == 1:
            return {"skills": ["sito-bloccato-cambia-fonte"], "origine": "selettore", "p": [0.83], "candidati": 3, "ms": 290, "motivo": ""}
        return {"skills": oro, "origine": "selettore", "p": [0.86] * len(oro), "candidati": 3, "ms": 280,
                "motivo": "" if oro else "regola"}

    def riuscita(op, braccio, blocco):
        if braccio == "A":
            return op["id"] in ("C03", "C22", "C18", "V04", "N02", "C09", "C10", "C20")
        if op["id"] == "V02":
            return False
        if op["id"] == "C10" and blocco == 1:
            return False
        return True

    def post_form(opener, percorso, campi, timeout=900):
        stato["turni"] += 1
        op = per_domanda[campi["message"]]
        braccio_blocco = campi["session"].rsplit("-", 2)[-2]
        braccio, blocco = braccio_blocco[0], int(braccio_blocco[1:])
        ev = []
        es = evento_skill(campi, op, braccio, blocco)
        if es is not None:
            ev.append(dict(es, type="skills_injected"))
        if op["azioni"]:
            ev.append({"type": "tool_start", "tool": "browser_open", "full_command": json.dumps({"url": "https://x.test"}), "round": 1})
            testa = STATO.get(op["id"], "cookie_banner: none")
            ev.append({"type": "tool_output", "tool": "browser_open", "output": f"{testa}\nPage URL: https://x.test\n--- page text ---\n...", "exit_code": 0})
            for extra in op["azioni"][1:]:
                if extra in ("browser_find", "browser_type", "browser_click", "browser_read"):
                    args = {"text": "x"} if extra == "browser_find" else ({"ref": "e1", "text": "x"} if extra == "browser_type" else ({"ref": "e1"} if extra == "browser_click" else {}))
                    ev.append({"type": "tool_start", "tool": extra, "full_command": json.dumps(args), "round": 2})
                    ev.append({"type": "tool_output", "tool": extra, "output": "ok", "exit_code": 0})
        testo = RISPOSTE_OK[op["id"]] if riuscita(op, braccio, blocco) else "Non ho trovato il dato sulla pagina."
        ev.append({"type": "agent_step", "round": 2})
        ev.append({"delta": testo})
        ev.append({"type": "metrics", "data": {"input_tokens": 9000, "output_tokens": 80,
                                               "usage_buckets": [{"input_tokens": 4400}, {"input_tokens": 4600}]}})
        return [f"data: {json.dumps(e)}\n".encode() for e in ev] + [b"data: [DONE]\n"]

    BB._client = lambda: None
    BB._leggi_credenziali = lambda: ("utente", "segreto")
    BB._post_json = lambda opener, percorso, corpo: {}
    BB._get_json = lambda opener, percorso: [{"id": "e1", "is_default": True, "default_model": "lfm"}]
    BB.gpu = lambda: "finta"
    BB.nuova_sessione = lambda opener, endpoint_id, modello, nome: nome
    BB._post_form = post_form
    manif = tmp / "manifesto.json"
    manif.write_text(json.dumps({"famiglia": "browser", "copiate": [{"nome": n} for n in
                                 ("articolo-lungo-trova-dato", "cerca-nel-sito", "sito-bloccato-cambia-fonte")],
                                 "gia_presenti": []}), encoding="utf-8")
    out = tmp / "famiglia"
    base = ["--ab-famiglia", "browser", "--manifesto", str(manif), "--out", str(out)]

    codice, testo = esci_con(BB.main, base + ["--tag", "F1"])
    controlla(codice == 0, f"A-B-B-A della famiglia completo (uscita {codice})")
    dati = json.loads((out / "banco-F1.json").read_text(encoding="utf-8"))
    bers = {"A05", "C03", "C04", "C05", "C11", "C18", "C22", "V01", "V02", "V03", "V04", "V05"}
    ops_viste = {t["op"] for t in dati["turni"]}
    controlla(ops_viste == bers | {"N02", "C09", "C10"}, f"bersagli di verifica della famiglia + controlli N02,C09,C10: {sorted(ops_viste)}")
    controlla(len(dati["turni"]) == 15 * 4, f"{len(dati['turni'])} turni (15 operazioni x 4 blocchi)")
    controlla(all(t["evento_skill"]["origine"] == ("banco" if t["braccio"] == "A" else "selettore") for t in dati["turni"]),
              "A in modo banco, B dal selettore")
    ref = (out / "verdetto-F1.md").read_text(encoding="utf-8")
    controlla('"verdetto": "TIENI"' in ref, "verdetto TIENI")
    controlla("C10 ciclo 1 blocco 1" in ref and "skill iniettate: sito-bloccato-cambia-fonte" in ref,
              "turno peggiorato con la skill iniettata nel referto")
    controlla("INSTALLATE.txt" in ref, "referto: nomi da aggiungere a INSTALLATE.txt")
    righe_f1 = (out / "banco-F1.txt").read_text(encoding="utf-8")
    controlla("ATTENZIONE: N02 B2" in righe_f1 and "selettore senza decisione (tetto)" in righe_f1,
              "un tetto isolato nel braccio B: avviso, il banco prosegue")
    n0 = stato["turni"]
    codice, _ = esci_con(BB.main, base + ["--tag", "F1", "--riprendi"])
    controlla(codice == 0 and stato["turni"] == n0, "--riprendi a banco completo non rifa' turni")

    for sc, attesa in (("leva_spenta", "ODYSSEUS_SKILL_SELETTORE=1"), ("a_senza_evento", "ODYSSEUS_BENCH_SKILL_FIELD=1"),
                       ("senza_candidati", "nessun candidato")):
        stato["scenario"] = sc
        codice, _ = esci_con(BB.main, base + ["--tag", f"X{sc}"])
        righe = (out / f"banco-X{sc}.txt").read_text(encoding="utf-8")
        controlla(codice == 2 and "STOP" in righe and attesa in righe, f"scenario {sc}: arresto con messaggio chiaro")

    # selettore acceso ma muto: arresto al terzo turno B di fila, prima di consumare l'A-B-B-A
    for sc in ("muto_nessuna decisione", "muto_tetto"):
        stato["scenario"] = sc
        tag = "X" + sc.replace(" ", "_")
        codice, _ = esci_con(BB.main, base + ["--tag", tag])
        righe = (out / f"banco-{tag}.txt").read_text(encoding="utf-8")
        turni = json.loads((out / f"banco-{tag}.json").read_text(encoding="utf-8"))["turni"]
        controlla(codice == 2 and "STOP" in righe and "3 turni B di fila senza decisione del selettore" in righe
                  and sum(t["braccio"] == "B" for t in turni) == 2 and not (out / f"verdetto-{tag}.md").exists(),
                  f"scenario {sc}: arresto dopo 3 turni B muti, nessun verdetto")
    # il selettore decide sempre "nessuna": il banco finisce ma il verdetto e' NON VALIDO, mai SCARTA
    stato["scenario"] = "regola_sempre"
    codice, _ = esci_con(BB.main, base + ["--tag", "Xregola"])
    ref = (out / "verdetto-Xregola.md").read_text(encoding="utf-8")
    controlla(codice == 3 and '"verdetto": "NON VALIDO"' in ref and "SCARTA" not in ref.split("```")[-1]
              and "Skill da togliere" not in ref and "nessun turno B sui bersagli ha iniettato skill" in ref,
              f"B senza iniezioni sui bersagli: NON VALIDO (uscita {codice}), nessuna skill da togliere")
    # dominio senza operazioni proprie: le operazioni del browser non valgono per un'altra famiglia
    codice, testo = esci_con(BB.main, ["--ab-famiglia", "osint", "--manifesto", str(manif), "--out", str(out),
                                       "--tag", "Xosint"])
    controlla(codice != 0 and "--ops" in testo, "--ab-famiglia osint senza --ops rifiutato")

    stato["scenario"] = "tieni"
    codice, testo = esci_con(BB.main, ["--ab-famiglia", "browser", "--manifesto", str(tmp / "assente.json"), "--out",
                                       str(out), "--tag", "F2", "--cicli", "1", "--bersagli", "A05,C03,A04"])
    controlla(codice != 0 and "SVILUPPO" in testo, "bersaglio di sviluppo rifiutato")

    stato["scenario"] = "classico"
    codice, _ = esci_con(BB.main, ["--ab", "sito-bloccato-cambia-fonte", "--bersagli", "C18,V03,V04",
                                   "--controlli", "N02,C09,C10", "--out", str(out), "--tag", "AB1"])
    controlla(codice == 0 and (out / "verdetto-AB1.md").exists(), "--ab classico invariato")
    for s in sorted(BIBLIOTECA.glob("*/*/SKILL.md")):
        codice, testo = esci_con(BB.main, ["--contaminazione", str(s)])
        controlla(codice == 0 and "PULITA" in testo, f"--contaminazione {s.parent.name}: PULITA")


# ------------------------------------------------------------------ parte 3: installatore
def parte_installatore(tmp: Path):
    print("== installa-biblioteca.py su DATA temporanee")
    py = sys.executable
    script = str(QUI / "installa-biblioteca.py")
    nomi = sorted(p.parent.name for p in (BIBLIOTECA / "browser").glob("*/SKILL.md"))
    dest, manif = tmp / "data1" / "skills", tmp / "prova1.json"

    def gira(*argomenti):
        r = subprocess.run([py, script, *argomenti], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout + r.stderr

    # una sola chiamata col cancello 1 vero (verifica-skill.py costa 1-2 minuti), le altre con verifica_molte finta
    codice, testo = gira("--prova-famiglia", "browser", "--dest", str(dest), "--manifesto", str(manif))
    controlla(codice == 0, f"--prova-famiglia browser (cancello 1 vero, uscita {codice})")
    copiate = sorted(p.parent.name for p in dest.glob("*/*/SKILL.md"))
    controlla(copiate == nomi, f"copiate le {len(nomi)} skill del dominio: {copiate}")
    m = json.loads(manif.read_text(encoding="utf-8"))
    controlla(len(m["copiate"]) == len(nomi) and m["famiglia"] == "browser", "manifesto con i file copiati")
    controlla(not list(dest.glob("*/*/PROVE.md")), "PROVE.md mai installato")
    codice, testo = gira("--prova-famiglia", "browser", "--dest", str(dest), "--manifesto", str(manif))
    controlla(codice == 2 and "prova in corso" in testo, "seconda prova rifiutata finche' c'e' il manifesto")
    estraneo = dest / "browser" / "cerca-nel-sito" / "nota-di-altri.txt"
    estraneo.write_text("non della prova", encoding="utf-8")
    codice, testo = gira("--togli-prova", "--dest", str(tmp / "altro"), "--manifesto", str(manif))
    controlla(codice == 2 and manif.exists(), "--togli-prova con --dest diverso dal manifesto rifiutato")
    codice, testo = gira("--togli-prova", "--dest", str(dest), "--manifesto", str(manif))
    controlla(codice == 0 and not manif.exists(), "--togli-prova: manifesto rimosso")
    controlla(not list(dest.glob("*/*/SKILL.md")), "--togli-prova: tolti tutti i SKILL.md copiati")
    controlla(estraneo.exists(), "--togli-prova: il file di altri resta (e la sua cartella)")
    controlla(not (dest / "browser" / "articolo-lungo-trova-dato").exists(), "--togli-prova: cartelle vuote create tolte")

    # le altre prove senza il cancello 1 vero (costa ~50 s): verifica_molte finta, stesso codice per il resto
    I = modulo("installa-biblioteca.py", "installa_biblioteca")
    sorgenti = sorted((BIBLIOTECA / "browser").glob("*/SKILL.md"))
    tutte_ok = {str(s.resolve()): [True, []] for s in sorgenti}
    ops_viste = []

    def finta(skill, operazioni):
        ops_viste.append(Path(operazioni))
        return dict(tutte_ok)
    I.verifica_molte = finta

    dest0, manif0 = tmp / "data0" / "skills", tmp / "prova0.json"
    codice, testo = esci_con(I.main, ["--prova-famiglia", "browser", "--prova", "--dest", str(dest0), "--manifesto", str(manif0)])
    controlla(codice == 0 and "[prova]" in testo and not dest0.exists() and not manif0.exists(),
              "--prova-famiglia --prova non scrive nulla")
    controlla(ops_viste and ops_viste[-1].name == "operazioni-browser.json",
              "cancello 1 della famiglia browser contro operazioni-browser.json")

    dest2, manif2 = tmp / "data2" / "skills", tmp / "prova2.json"
    altra = dest2 / "browser" / "cerca-nel-sito" / "SKILL.md"
    altra.parent.mkdir(parents=True)
    altra.write_text("---\nname: cerca-nel-sito\ndescription: di un altro\n---\n", encoding="utf-8")
    codice, testo = esci_con(I.main, ["--prova-famiglia", "browser", "--dest", str(dest2), "--manifesto", str(manif2)])
    controlla(codice == 2 and "non la sovrascrivo" in testo, "skill non della biblioteca con lo stesso nome: fermo")
    controlla(not manif2.exists() and sorted(p.parent.name for p in dest2.glob("*/*/SKILL.md")) == ["cerca-nel-sito"]
              and "di un altro" in altra.read_text(encoding="utf-8"), "niente copiato, la skill di altri intatta")

    dest3, manif3 = tmp / "data3" / "skills", tmp / "prova3.json"
    gemella = dest3 / "browser" / "articolo-lungo-trova-dato" / "SKILL.md"
    gemella.parent.mkdir(parents=True)
    shutil.copyfile(BIBLIOTECA / "browser" / "articolo-lungo-trova-dato" / "SKILL.md", gemella)
    codice, testo = esci_con(I.main, ["--prova-famiglia", "browser", "--dest", str(dest3), "--manifesto", str(manif3)])
    m3 = json.loads(manif3.read_text(encoding="utf-8")) if manif3.exists() else {}
    controlla(codice == 0 and [x["nome"] for x in m3.get("gia_presenti", [])] == ["articolo-lungo-trova-dato"]
              and len(m3.get("copiate", [])) == len(nomi) - 1, "skill gia' presente identica: registrata, non copiata")
    codice, testo = esci_con(I.main, ["--togli-prova", "--manifesto", str(manif3)])
    controlla(codice == 0 and gemella.exists() and len(list(dest3.glob("*/*/SKILL.md"))) == 1,
              "--togli-prova lascia la skill che c'era gia'")

    dest4, manif4 = tmp / "data4" / "skills", tmp / "prova4.json"
    un_errore = dict(tutte_ok)
    un_errore[str(sorgenti[0].resolve())] = [False, ["ERRORE  finto"]]
    I.verifica_molte = lambda skill, operazioni: dict(un_errore)
    codice, testo = esci_con(I.main, ["--prova-famiglia", "browser", "--dest", str(dest4), "--manifesto", str(manif4)])
    m4 = json.loads(manif4.read_text(encoding="utf-8")) if manif4.exists() else {}
    controlla(codice == 0 and sorgenti[0].parent.name not in [x["nome"] for x in m4.get("copiate", [])]
              and [x["nome"] for x in m4.get("scartate", [])] == [sorgenti[0].parent.name],
              "skill che non passa il cancello 1: scartata, le altre installate")
    esci_con(I.main, ["--togli-prova", "--manifesto", str(manif4)])
    controlla(not dest4.parent.exists(), "--togli-prova: tolta anche la DATA temporanea creata dalla prova")

    # skill RISCRITTA da altri durante la prova (UI del proprietario, manage_skills): --togli-prova non la tocca
    I.verifica_molte = finta
    dest5, manif5 = tmp / "data5" / "skills", tmp / "prova5.json"
    esci_con(I.main, ["--prova-famiglia", "browser", "--dest", str(dest5), "--manifesto", str(manif5)])
    riscritta = dest5 / "browser" / "cerca-nel-sito" / "SKILL.md"
    testo_suo = "---\nname: cerca-nel-sito\ndescription: \"riscritta dal proprietario durante la prova\"\n---\n"
    riscritta.write_text(testo_suo, encoding="utf-8")
    codice, testo = esci_con(I.main, ["--togli-prova", "--manifesto", str(manif5)])
    controlla(codice == 3 and riscritta.exists() and riscritta.read_text(encoding="utf-8") == testo_suo
              and manif5.exists() and "[resta]" in testo and len(list(dest5.glob("*/*/SKILL.md"))) == 1,
              f"skill riscritta durante la prova: resta (uscita {codice}), manifesto lasciato, le altre tolte")
    codice, testo = esci_con(I.main, ["--prova-famiglia", "browser", "--dest", str(dest5), "--manifesto", str(manif5)])
    controlla(codice == 2 and "prova in corso" in testo, "finche' non si decide, nessuna prova nuova")
    codice, testo = esci_con(I.main, ["--togli-prova", "--tieni-cambiate", "--manifesto", str(manif5)])
    controlla(codice == 0 and not manif5.exists() and riscritta.read_text(encoding="utf-8") == testo_suo,
              "--tieni-cambiate: il file riscritto resta, la prova e' chiusa")

    # contaminazione: le operazioni di verifica del dominio della famiglia, mai quelle del browser per ripiego
    bib = tmp / "biblio"
    (bib / "osint" / "notizia-verifica").mkdir(parents=True)
    (bib / "osint" / "notizia-verifica" / "SKILL.md").write_text(
        "---\nname: notizia-verifica\ncategory: osint\n---\n", encoding="utf-8")
    I.BIBLIOTECA, I.ELENCO = bib, bib / "INSTALLATE.txt"
    I.verifica_molte = finta
    ops_viste.clear()
    dest6, manif6 = tmp / "data6" / "skills", tmp / "prova6.json"
    codice, testo = esci_con(I.main, ["--prova-famiglia", "osint", "--dest", str(dest6), "--manifesto", str(manif6)])
    controlla(codice == 2 and "operazioni-osint.json" in testo and not ops_viste and not manif6.exists(),
              "--prova-famiglia osint senza operazioni-osint.json: ferma prima del cancello 1")
    ops_osint = tmp / "operazioni-osint-finte.json"
    ops_osint.write_text(json.dumps({"operazioni": []}), encoding="utf-8")
    codice, testo = esci_con(I.main, ["--prova-famiglia", "osint", "--operazioni", str(ops_osint), "--prova",
                                      "--dest", str(dest6), "--manifesto", str(manif6)])
    controlla(ops_viste and ops_viste[-1] == ops_osint, f"--operazioni FILE passato al cancello 1: {ops_viste[-1:]}")
    I.ELENCO.write_text("notizia-verifica\n", encoding="utf-8")
    I.verifica = lambda skill, operazioni: True
    codice, testo = esci_con(I.main, ["--prova", "--dest", str(dest6)])
    controlla(codice == 1 and "[scartata] notizia-verifica" in testo and "operazioni-osint.json" in testo,
              "installazione normale: skill osint senza le sue operazioni di verifica scartata")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parte", choices=["selettore", "famiglia", "installatore", "tutte"], default="tutte")
    ap.add_argument("--tmp", type=Path, default=None, help="cartella di lavoro (predefinita: temporanea, poi cancellata)")
    a = ap.parse_args()
    if a.parte == "tutte":
        codici = []
        for parte in ("installatore", "famiglia", "selettore"):
            argomenti = [sys.executable, str(Path(__file__).resolve()), "--parte", parte]
            if a.tmp:
                argomenti += ["--tmp", str(a.tmp / parte)]
            codici.append(subprocess.run(argomenti).returncode)
        print("PROVE OFFLINE: " + ("TUTTE OK" if not any(codici) else f"FALLITE (uscite {codici})"))
        return 1 if any(codici) else 0
    tmp = a.tmp or Path(tempfile.mkdtemp(prefix=f"prova-{a.parte}-"))
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        {"selettore": parte_selettore, "famiglia": parte_famiglia, "installatore": parte_installatore}[a.parte](tmp)
    finally:
        if a.tmp is None:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"parte {a.parte}: " + ("OK" if not FALLITE else f"{len(FALLITE)} controlli falliti"))
    return 1 if FALLITE else 0


if __name__ == "__main__":
    sys.exit(main())
