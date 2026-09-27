r"""Banco del SELETTORE delle skill: cancello 2 della biblioteca (stanza 3, 27 set 2026).

Decisione del proprietario: D:\vergilius-lab\chatroom\stanza3-biblioteca-skill\EMENDAMENTO-ADRIAN-27SET.md (tre cancelli:
1 statico per tutte, 2 questo banco, 3 A/B per famiglia). Piano: ...\materiale\SELETTORE\PLAN.md (obiettivo 2) e
obiettivo2.md (punto 2.5). Base: scripts\banco-system-one.py (Registro, Server, Modello, preflight, --dry-run, --riprendi).

Misura la SOLA decisione del selettore, niente agente: per ogni messaggio del dataset il prompt di PRODUZIONE va a
/completion di llama-swap (/upstream/<modello>/completion) su uno slot fisso, svuotato dopo ogni richiesta come fa
system_one.decidi(). Tutto cio' che decide viene importato in sola lettura da odysseus:
  src/skill_selettore.py        candidati (stadio 1, prefiltro oltre 8), opzioni, prompt_selettore, regola
  src/shadowbroker/system_one   payload, leggi_probabilita, MASSA_MINIMA
  services/memory/skill_format  lettura dei SKILL.md (come SkillsManager.load_all)
  services/memory/skills        get_relevant_skills (braccio J e prefiltro lessicale)
Le skill candidate si leggono dalla BIBLIOTECA (biblioteca-skill\<dominio>\...), non da odysseus\data; --skill-dir aggiunge
una cartella di prova (es. lo staging dello sciame; stesso nome = la versione di prova sostituisce quella della biblioteca).

Bracci:
  J    Jaccard di oggi da solo (get_relevant_skills, soglia 0,25, max 3, come agent_loop "Inject relevant skills"),
       sulle stesse candidate dello stadio 1, senza la soppressione dei turni a basso segnale: offline, nessuna rete;
  S    System One con "nessuna" ultima (produzione con ODYSSEUS_SKILL_SELETTORE_NESSUNA_PRIMA=0);
  S'   System One con "nessuna" prima (sfrutta il bias verso la lettera A in direzione prudente).
Regole ricalcolate offline sulla distribuzione salvata: produzione (prefisso con massa >= soglia, 1-2 skill, mai con
"nessuna"), r1 (top-1 >= 0,7), r3 (top-1 >= 0,7 piu' top-2 se >= 0,3); tabella delle soglie sulla meta' di TARATURA.

Dataset (banco-selettore-<dominio>.json accanto a questo file): operazioni del banco d'uso con domanda e domanda_alt
(etichette = skill_attese, oppure oro_messaggio del dataset quando l'oro non si deduce dal solo messaggio) + messaggi
scritti apposta, meno le voci in "escluse" (oro non decidibile dal messaggio); oro = mappa_oro[etichetta] = nome della
skill della biblioteca, le etichette senza skill contano come "nessuna". Divisione STABILE: operazioni per ruolo
(sviluppo -> taratura, verifica -> verifica: le due formulazioni stanno sempre nella stessa meta'), messaggi scritti col
campo "meta" del dataset o, se manca (messaggi nuovi), con l'hash dell'id (sha256(gruppo) mod 100 < 50 = verifica):
ne' una riga nuova in mappa_oro ne' un messaggio in piu' spostano le voci vecchie. Una voce che cambia meta' rispetto ai
banchi gia' registrati in --out ferma il banco (fuga fra taratura e verifica). --seme decide solo l'ordine delle richieste.
VERDETTO SOLO SULLA META' DI VERIFICA, e solo su un registro COMPLETO (voci con candidati x bracci x passate richieste):
se manca anche una risposta l'esito e' INCOMPLETO (uscita 1), con l'elenco delle mancanti e --riprendi.

Passate: "vuoto" (slot del banco e slot 0 svuotati) e "chat8k" (una chat finta di ~8200 token ferma nello slot 0, la
condizione del referto System One). Lo slot 0 serve SOLO a questo carico: si svuota all'inizio di ogni passata e alla
fine di chat8k (la chat vera in cache, se c'era, si ricalcola al prossimo messaggio). Le decisioni non vanno mai negli
slot 0 e 3. Qualita' e latenza del verdetto si leggono sulla passata chat8k (se c'e').

Criteri per accendere la leva (obiettivo 2, per braccio S e S', regola di produzione):
  iniezioni sbagliate <= 10% delle iniezioni; iniezioni sui casi "nessuna" <= 10%; richiamo >= 60%; F1 > braccio J;
  latenza mediana <= 0,35 s e p90 <= 0,5 s con chat 8k; tetto (0,8 s, candidati + richiesta + svuotamento) superato
  in <= 2% dei casi.

Uso (odysseus\venv: serve importare src.skill_selettore; niente jinja2, il template e' quello reso a mano da system_one):
  odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser --dry-run
  odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser
  odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser --skill-dir D:\vergilius-lab\biblioteca-staging\browser --tag staging
  odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser --riprendi <file.jsonl>
  odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser --riepiloga <file.jsonl>
Uscite (--out, default D:\vergilius-lab\ricerche\skill\banco-selettore): selettore-<dominio>[-tag]-<data>.jsonl (una
riga per richiesta, scritta subito), .txt (righe di avanzamento), -riepilogo.json; --dry-run: dryrun-<dominio>-<data>.json.
Regole: nessun servizio avviato da qui; mai lfm-uncensored; stack acceso ma fermo (nessuna chat in corso).
"""
from __future__ import annotations

import argparse
import atexit
import datetime as dt
import hashlib
import importlib.util
import json
import os
import random
import shutil
import sys
import tempfile
import time
import urllib.error
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True  # odysseus si legge soltanto: niente __pycache__ nuovi
# Gli import di odysseus (services/__init__, agent_loop) creano e scrivono il database di DATA_DIR (app.db, cache,
# logs): con la DATA vera ogni --dry-run o --riepiloga toccava odysseus\data\app.db. Il banco non legge nulla da
# DATA_DIR (skill dalla biblioteca, soglie dall'ambiente): una DATA temporanea, tolta all'uscita.
_DATA_TEMPORANEA = tempfile.mkdtemp(prefix="banco-selettore-data-")
os.environ["ODYSSEUS_DATA_DIR"] = _DATA_TEMPORANEA


def _togli_data_temporanea() -> None:
    db = sys.modules.get("core.database")  # su Windows app.db resta bloccato finche' il motore SQLite e' aperto
    try:
        if db is not None:
            db.engine.dispose()
    except Exception:  # noqa: BLE001
        pass
    shutil.rmtree(_DATA_TEMPORANEA, ignore_errors=True)


atexit.register(_togli_data_temporanea)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

QUI = Path(__file__).resolve().parent
RADICE = QUI.parent
ODYSSEUS = Path(os.environ.get("VERGILIUS_ODYSSEUS_DIR") or (RADICE / "odysseus"))
BIBLIOTECA = RADICE / "biblioteca-skill"
MISURE = Path(r"D:\vergilius-lab\ricerche\skill\banco-selettore")
SEME = 2709
QUOTA_HASH_VERIFICA = 50  # messaggi scritti senza campo meta: sha256(gruppo) mod 100 < 50 -> verifica (fissata, mai cambiarla)
META = ("taratura", "verifica")
BRACCI = {"S": False, "S'": True}  # braccio -> "nessuna" prima
PASSATE = ("vuoto", "chat8k")
SLOT_VIETATI = (0, 3)
CLASSI = ("nessuna", "una", "due")
J_SOGLIA, J_MAX, J_CONF = 0.25, 3, 0.85  # agent_loop.py, blocco "Inject relevant skills" (get_relevant_skills)
R_TOP1, R_TOP2 = 0.7, 0.3               # regole r1/r3 di obiettivo2.md (2.1 punto 4)
CRITERI = {"sbagliate_max": 0.10, "su_nessuna_max": 0.10, "richiamo_min": 0.60,
           "lat_mediana_max": 0.35, "lat_p90_max": 0.5, "tetto_max": 0.02}
CHAT_TOKEN = 8200
# Modi accesi per dominio (chiavi di skill_selettore.domini); browser = modulo del banco d'uso (vista + browser).
MODI_PER_DOMINIO = {"browser": {"vista": True, "browser": True}, "pc": {"vista": True, "computer": True},
                    "osint": {"osint": True}, "finanza": {"osint": True, "finanza": True},
                    "voce": {"voce": True}, "generale": {}, "file": {}}

sys.path.insert(0, str(ODYSSEUS))
try:
    from src import skill_selettore as SEL          # noqa: E402
    from src.shadowbroker import system_one as S1   # noqa: E402
    from services.memory.skill_format import Skill  # noqa: E402
    from services.memory.skills import SkillsManager  # noqa: E402
except Exception as _e:  # noqa: BLE001
    raise SystemExit(f"codice di produzione non importabile da {ODYSSEUS}: {_e!r}. "
                     "Usa odysseus\\venv\\Scripts\\python.exe")


def _vicino(nome_file: str, nome_mod: str):
    spec = importlib.util.spec_from_file_location(nome_mod, QUI / nome_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BSO = _vicino("banco-system-one.py", "banco_system_one")  # Registro, Server, Modello, pct, mediana
Registro = BSO.Registro


def crea_server(base: str, modello: str, reg):
    """Punto unico di accesso alla rete (la prova offline lo sostituisce con un server finto)."""
    return BSO.Server(base, modello, reg)


def sha(x) -> str:
    return hashlib.sha256(x.encode("utf-8") if isinstance(x, str) else x).hexdigest()[:16]


def classe(oro) -> str:
    return CLASSI[min(len(oro), 2)]


# ------------------------------------------------------------------ skill della biblioteca
def cartelle_skill(args) -> list:
    out = [] if args.senza_biblioteca else [BIBLIOTECA / args.famiglia]
    return out + [Path(p) for p in (args.skill_dir or [])]


def carica_skill(cartelle, owner: str) -> tuple:
    """SKILL.md -> dict come SkillsManager.load_all (Skill.from_markdown(...).to_dict()). Filtro owner come
    SkillsManager.load(owner=...): una skill di un altro proprietario in produzione non si vede."""
    per_nome, note = {}, []
    for c in cartelle:
        if not Path(c).is_dir():
            raise SystemExit(f"cartella delle skill assente: {c}")
        for f in sorted(Path(c).rglob("SKILL.md")):
            testo = f.read_text(encoding="utf-8")
            d = Skill.from_markdown(testo, path=str(f)).to_dict()
            d["_file"], d["_sha"] = str(f), sha(testo)
            if owner and str(d.get("owner") or "") != owner:
                note.append(f"{d['name']}: owner {d.get('owner')!r} e non {owner!r}: in produzione non si vede (esclusa)")
                continue
            if d["name"] in per_nome:
                note.append(f"{d['name']}: {f} sostituisce {per_nome[d['name']]['_file']}")
            per_nome[d["name"]] = d
    return sorted(per_nome.values(), key=lambda s: (s.get("category") or "", s["name"])), note


def paniere_forzato(modi: dict):
    """Strumenti che il modo mette di sicuro nel paniere: stessa costruzione di routes/chat_routes.py
    `_forzati_per_selettore` (non importabile qui: la rotta apre il database), senza ricerca web come il banco d'uso.
    None = paniere non noto offline (computer_mode: gli strumenti MCP di Windows esistono solo a stack acceso)."""
    from src.tool_index import ALWAYS_AVAILABLE
    nomi = set(ALWAYS_AVAILABLE)
    if modi.get("osint"):
        from src.agent_tools import FINANCE_TOOL_NAMES, OSINT_TOOL_NAMES
        nomi |= set(OSINT_TOOL_NAMES)
        if modi.get("finanza"):
            nomi |= set(FINANCE_TOOL_NAMES)  # approssimazione larga di _strumenti_del_profilo(financial=True)
    if modi.get("vista"):
        from src.agent_tools import VISTA_TOOL_NAMES
        nomi |= set(VISTA_TOOL_NAMES)
        if modi.get("browser"):
            from src.browser_tooling_constants import BROWSER_CORE_TOOL_NAMES
            nomi |= set(BROWSER_CORE_TOOL_NAMES)
        if modi.get("computer"):
            return None
    return nomi


def perche_scartata(s: dict, domini: set, paniere) -> str:
    """Diagnosi dello stadio 1 per una skill che non entra fra le candidate (stesse prove di SEL.candidata)."""
    if str(s.get("source") or "").strip().casefold() != "user":
        return f"source {s.get('source')!r} (serve user)"
    if not SEL.strumenti(s):
        return "campo tools: vuoto"
    if str(s.get("status") or "").strip().casefold() != "published":
        return f"status {s.get('status')!r}"
    if str(s.get("category") or "").strip().casefold() not in domini:
        return f"category {s.get('category')!r} fuori dai domini {sorted(domini)}"
    if not str(s.get("description") or "").strip():
        return "description vuota"
    if paniere is not None:
        fuori = [t for t in SEL.strumenti(s) if t not in paniere]
        if fuori:
            return f"strumenti fuori dal paniere del modo: {fuori}"
    try:
        from src.agent_loop import _skill_provenance_is_local
    except Exception as e:  # noqa: BLE001
        return f"src.agent_loop non importabile ({type(e).__name__}): candidata() la scarta sempre"
    if not _skill_provenance_is_local(dict(s)):
        return "provenienza non locale (category imported o 'Imported from')"
    return "?"


def gestore_senza_disco():
    """SkillsManager senza __init__ (che crea cartelle): get_relevant_skills con skills passate non tocca il disco."""
    return SkillsManager.__new__(SkillsManager)


# ------------------------------------------------------------------ dataset
def _per_voce(tabella: dict, vid: str, gruppo: str):
    """oro_messaggio / escluse: la chiave 'ID-d' (una formulazione) vale piu' di 'ID' (tutte e due)."""
    if vid in tabella:
        return tabella[vid]
    return tabella.get(gruppo)


def carica_dataset(percorso: Path) -> tuple:
    grezzo = percorso.read_bytes()
    dati = json.loads(grezzo.decode("utf-8"))
    f_ops = (percorso.parent / dati["operazioni"]).resolve()
    grezzo_ops = f_ops.read_bytes()
    ops = json.loads(grezzo_ops.decode("utf-8"))["operazioni"]
    mappa = dict(dati.get("mappa_oro") or {})
    oro_msg = dict(dati.get("oro_messaggio") or {})  # etichette dal SOLO messaggio (al posto di skill_attese)
    escluse = dict(dati.get("escluse") or {})        # voci con oro non decidibile dal messaggio: fuori dal banco
    problemi = []
    voci = []
    for o in ops:
        for campo, suff in (("domanda", "d"), ("domanda_alt", "a")):
            if o.get(campo):
                vid = f"{o['id']}-{suff}"
                et_op = list(o.get("skill_attese") or [])
                riscritto = _per_voce(oro_msg, vid, o["id"])
                voci.append({"id": vid, "gruppo": o["id"], "testo": o[campo],
                             "etichette": list(riscritto) if riscritto is not None else et_op,
                             "etichette_op": et_op, "oro_messaggio": riscritto is not None,
                             "origine": f"operazione {campo}", "ruolo_op": o.get("ruolo") or "sviluppo",
                             "meta_json": None})
    id_op = {v["id"] for v in voci} | {v["gruppo"] for v in voci}
    for m in dati.get("messaggi") or []:
        voci.append({"id": m.get("id"), "gruppo": m.get("gruppo") or m.get("id"), "testo": m.get("testo"),
                     "etichette": list(m.get("etichette") or []), "etichette_op": None, "oro_messaggio": False,
                     "origine": "scritto", "ruolo_op": None, "meta_json": m.get("meta")})
    for k, et in oro_msg.items():
        if k not in id_op:
            problemi.append(f"oro_messaggio: {k!r} non e' un'operazione ne' una sua formulazione (ID o ID-d/ID-a)")
        elif not isinstance(et, list):
            problemi.append(f"oro_messaggio: {k!r} deve essere una lista di etichette")
    tutte = id_op | {v["id"] for v in voci} | {v["gruppo"] for v in voci}
    for k, motivo in escluse.items():
        if k not in tutte:
            problemi.append(f"escluse: {k!r} non e' una voce del dataset")
        if not str(motivo or "").strip():
            problemi.append(f"escluse: {k!r} senza motivo")
    fuori = {v["id"]: _per_voce(escluse, v["id"], v["gruppo"]) for v in voci
             if _per_voce(escluse, v["id"], v["gruppo"]) is not None}
    voci = [v for v in voci if v["id"] not in fuori]
    for v in voci:
        v["oro"] = sorted({mappa[e] for e in v["etichette"] if e in mappa})
        v["classe"] = classe(v["oro"])
    vocabolario = {e for o in ops for e in (o.get("skill_attese") or [])} | set(dati.get("etichette_extra") or [])
    info = {"dataset": str(percorso), "dataset_sha": sha(grezzo), "operazioni": str(f_ops),
            "operazioni_sha": sha(grezzo_ops), "mappa_oro": mappa, "dominio": dati.get("dominio"),
            "modi": dati.get("modi"), "vocabolario": sorted(vocabolario), "escluse": fuori,
            "problemi": problemi}
    return voci, info


def meta_da_hash(gruppo: str) -> str:
    """Meta' di un messaggio scritto senza campo meta: dipende SOLO dal suo id (mai dalla mappa, mai dagli altri)."""
    return "verifica" if int(hashlib.sha256(str(gruppo).encode("utf-8")).hexdigest(), 16) % 100 < QUOTA_HASH_VERIFICA \
        else "taratura"


def dividi(voci: list) -> dict:
    """Taratura/verifica STABILE. Operazioni: per ruolo (le due formulazioni nella stessa meta'). Messaggi scritti:
    campo meta del dataset (congelato), altrimenti hash dell'id. Nessuna dipendenza da mappa_oro, dalle classi o dal
    numero di voci: aggiungere una skill o un messaggio non sposta nessuna voce gia' assegnata."""
    meta = {}
    for v in voci:
        if v["origine"] != "scritto":
            meta[v["gruppo"]] = "verifica" if v["ruolo_op"] == "verifica" else "taratura"
    for v in voci:
        if v["origine"] == "scritto":
            v["meta_da"] = "dataset" if v.get("meta_json") else "hash"
            m = v["meta_json"] if v.get("meta_json") else meta_da_hash(v["gruppo"])
            meta.setdefault(v["gruppo"], m)
    for v in voci:
        v["meta"] = v["meta_json"] if v.get("meta_json") else meta[v["gruppo"]]
    return meta


def storico_divisione(out: Path, famiglia: str, voci: list) -> list:
    """Voci che hanno cambiato meta' rispetto ai banchi gia' registrati (intestazioni dei jsonl in --out): una voce
    vista in taratura non deve mai finire in verifica (le description si riscrivono sulla taratura), ne' il contrario."""
    errori = []
    ora = {v["id"]: v["meta"] for v in voci}
    registri = sorted(Path(out).glob(f"selettore-{famiglia}*.jsonl")) if Path(out).is_dir() else []
    for f in registri:
        testa = None
        try:
            with open(f, encoding="utf-8") as fh:
                for riga, _ in zip(fh, range(5)):  # l'intestazione e' la prima riga di ogni registro
                    x = json.loads(riga) if riga.strip() else {}
                    if x.get("tipo") == "intestazione":
                        testa = x
                        break
        except (OSError, json.JSONDecodeError):
            continue
        prima = (testa or {}).get("meta_per_id") or {}
        spostate = sorted(i for i, m in prima.items() if i in ora and ora[i] != m)
        if spostate:
            errori.append(f"divisione cambiata rispetto a {f.name}: {', '.join(f'{i} {prima[i]}->{ora[i]}' for i in spostate[:12])}"
                          + (f" (e altre {len(spostate) - 12})" if len(spostate) > 12 else "")
                          + ": fuga fra taratura e verifica. Rimetti la meta' di prima (campo meta nel dataset); "
                            "solo se la nuova divisione e' voluta, sposta i banchi vecchi fuori da --out")
    return errori


def valida(voci: list, info: dict, nomi_skill: set) -> tuple:
    errori, avvisi = list(info.get("problemi") or []), []
    visti = set()
    id_operazioni = {v["gruppo"] for v in voci if v["origine"] != "scritto"}
    for v in voci:
        if v["origine"] == "scritto" and v["gruppo"] in id_operazioni:
            errori.append(f"{v['id']}: gruppo {v['gruppo']!r} uguale a un'operazione (sposterebbe la sua meta')")
        if v.get("meta_json") is not None and v["meta_json"] not in META:
            errori.append(f"{v.get('id')}: meta {v['meta_json']!r} (ammesse {', '.join(META)})")
        vid = v.get("id") or "?"
        if not v.get("id") or not str(v.get("testo") or "").strip():
            errori.append(f"{vid}: id o testo mancante")
        if vid in visti:
            errori.append(f"{vid}: id duplicato")
        visti.add(vid)
        if "\u2014" in str(v.get("testo") or ""):
            errori.append(f"{vid}: carattere vietato (trattino lungo)")
        for e in v["etichette"]:
            if e not in info["vocabolario"]:
                errori.append(f"{vid}: etichetta sconosciuta {e!r} (refuso? verrebbe letta come 'nessuna')")
        if len(v["oro"]) > 2:
            avvisi.append(f"{vid}: {len(v['oro'])} skill d'oro, il selettore ne inietta al massimo 2")
    for et, nome in info["mappa_oro"].items():
        if nome not in nomi_skill:
            errori.append(f"mappa_oro: {et} -> {nome}, skill assente fra quelle caricate {sorted(nomi_skill)}")
    n = len(voci)
    c = Counter(v["classe"] for v in voci)
    if n < 120:
        errori.append(f"{n} voci (servono almeno 120)")
    if n and c["nessuna"] / n < 0.25:
        errori.append(f"voci 'nessuna' {c['nessuna']}/{n} (servono almeno 25%)")
    if n and c["due"] / n < 0.10:
        errori.append(f"voci con due skill {c['due']}/{n} (servono almeno 10%)")
    per_gruppo = {}
    for v in voci:
        per_gruppo.setdefault(v["gruppo"], set()).add(v.get("meta"))
    for g, mm in per_gruppo.items():
        if len(mm) > 1:
            errori.append(f"gruppo {g}: formulazioni in meta' diverse {sorted(mm)}")
    ver = [v for v in voci if v.get("meta") == "verifica"]
    cv = Counter(v["classe"] for v in ver)
    for k in CLASSI:
        if not cv[k]:
            avvisi.append(f"meta' di verifica senza voci di classe {k!r}")
    return errori, avvisi


# ------------------------------------------------------------------ decisione (codice di produzione)
def candidate_di(skills: list, modi: dict, paniere, testo: str, gestore) -> tuple:
    """(candidate del selettore, tutte le candidate dello stadio 1 per il braccio J)."""
    dom = SEL.domini(modi)
    cand = SEL.candidati(skills, domini_ammessi=dom, strumenti_ammessi=paniere, messaggio=testo, gestore=gestore)
    tutte = SEL.candidati(skills, domini_ammessi=dom, strumenti_ammessi=paniere, messaggio=testo, gestore=None,
                          limite=10 ** 6)
    return cand, tutte


def braccio_j(gestore, testo: str, tutte: list) -> list:
    scelte = gestore.get_relevant_skills(testo, skills=[dict(s) for s in tutte], threshold=J_SOGLIA,
                                         max_items=J_MAX, min_confidence=J_CONF)
    return [str(s.get("name")) for s in scelte]


def lettere_di(cand: list, prima: bool) -> tuple:
    testi, per_lettera = SEL.opzioni(cand, prima)
    lettere = S1.LETTERE[:len(testi)]
    mappa = {L: (str(per_lettera[i]["name"]) if per_lettera[i] is not None else SEL.NESSUNA)
             for i, L in enumerate(lettere)}
    nessuna = lettere[per_lettera.index(None)]
    return testi, mappa, nessuna


def regole(prob: dict, mappa: dict, nessuna: str, massa, soglia: float, massimo: int) -> dict:
    """Scelte (nomi) per regola dalla distribuzione sulle lettere. Produzione: voto None o massa sotto
    MASSA_MINIMA = nessuna decisione = zero skill (system_one.decidi)."""
    if not prob or massa is None or massa < S1.MASSA_MINIMA:
        return {"produzione": [], "r1": [], "r3": []}
    prod = [mappa[L] for L in SEL.regola(prob, nessuna, soglia, massimo)]
    ordinate = sorted(prob.items(), key=lambda kv: (-kv[1], kv[0]))
    r1 = [mappa[ordinate[0][0]]] if ordinate[0][1] >= R_TOP1 and ordinate[0][0] != nessuna else []
    r3 = list(r1)
    if r1 and massimo >= 2 and len(ordinate) > 1 and ordinate[1][1] >= R_TOP2 and ordinate[1][0] != nessuna:
        r3.append(mappa[ordinate[1][0]])
    return {"produzione": prod, "r1": r1, "r3": r3}


# ------------------------------------------------------------------ metriche
def misura(coppie: list) -> dict:
    """coppie = [(oro, scelte)]. Iniezioni contate per skill; richiamo sulle skill d'oro; F1 micro."""
    n = len(coppie)
    iniezioni = giuste = oro_tot = su_nessuna = n_nessuna = esatte = 0
    per_skill, per_classe = {}, {k: {"n": 0, "esatte": 0} for k in CLASSI}
    for oro, sc in coppie:
        o, s = set(oro), set(sc)
        iniezioni += len(s)
        giuste += len(s & o)
        oro_tot += len(o)
        if not o:
            n_nessuna += 1
            su_nessuna += bool(s)
        esatte += s == o
        pc = per_classe[classe(o)]
        pc["n"] += 1
        pc["esatte"] += s == o
        for x in s | o:
            d = per_skill.setdefault(x, {"iniettata": 0, "giusta": 0, "oro": 0})
            d["iniettata"] += x in s
            d["giusta"] += x in s and x in o
            d["oro"] += x in o
    prec = giuste / iniezioni if iniezioni else None
    rich = giuste / oro_tot if oro_tot else None
    f1 = 2 * prec * rich / (prec + rich) if prec and rich else 0.0
    return {"n": n, "iniezioni": iniezioni, "giuste": giuste, "sbagliate": iniezioni - giuste,
            "quota_sbagliate": (iniezioni - giuste) / iniezioni if iniezioni else 0.0,
            "casi_nessuna": n_nessuna, "iniezioni_su_nessuna": su_nessuna,
            "quota_su_nessuna": su_nessuna / n_nessuna if n_nessuna else 0.0,
            "skill_oro": oro_tot, "richiamo": rich, "precisione": prec, "f1": f1,
            "esatte": esatte, "quota_esatte": esatte / n if n else None, "per_classe": per_classe,
            "per_skill": per_skill}


def criteri(m: dict, mj: dict, lat: dict, tetto_q, passata: str) -> dict:
    con_chat = passata == "chat8k"
    c = {"1_sbagliate": m["quota_sbagliate"] <= CRITERI["sbagliate_max"],
         "2_su_nessuna": m["quota_su_nessuna"] <= CRITERI["su_nessuna_max"],
         "3_richiamo": (m["richiamo"] or 0.0) >= CRITERI["richiamo_min"],
         "4_f1_contro_J": m["f1"] > mj["f1"],
         "5_latenza_chat8k": bool(con_chat and lat and lat["mediana"] is not None
                                  and lat["mediana"] <= CRITERI["lat_mediana_max"]
                                  and lat["p90"] <= CRITERI["lat_p90_max"]),
         "6_tetto": bool(con_chat and tetto_q is not None and tetto_q <= CRITERI["tetto_max"])}
    manca = [k for k, ok in c.items() if not ok]
    esito = "ACCENDI" if not manca else "NON ACCENDERE"
    nota = "" if con_chat else "passata chat8k assente: latenza e tetto non valutabili"
    return {"criteri": c, "falliti": manca, "esito": esito, "nota": nota}


def completezza(records: list) -> dict:
    """Risposte attese (voci con candidati x bracci x passate richieste, dall'intestazione) contro registrate.
    Senza elenco atteso (registro di una versione vecchia) lo si ricostruisce dal braccio J e dagli argomenti."""
    teste = [r for r in records if r.get("tipo") in ("intestazione", "ripresa")]
    prima = next((r for r in teste if r.get("tipo") == "intestazione"), None)
    avvisi = []
    att = (prima or {}).get("attese")
    if att:
        ids, bracci = list(att.get("ids") or []), list(att.get("bracci") or BRACCI)
        chieste = {p for t in teste for p in ((t.get("attese") or {}).get("passate") or [])}
    else:
        ids = sorted(r["id"] for r in records if r.get("tipo") == "j" and r.get("candidati"))
        bracci = list(BRACCI)
        chieste = {p.strip() for t in teste for p in str((t.get("argomenti") or {}).get("passate") or "").split(",")
                   if p.strip()}
        avvisi.append("intestazione senza elenco delle risposte attese: ricostruito dal braccio J e dagli argomenti"
                      if prima else "registro senza intestazione: attese tutte le passate")
        chieste = chieste or set(PASSATE)
    passate = [p for p in PASSATE if p in chieste]
    fatte = {(r["braccio"], r["passata"], r["id"]) for r in records if r.get("tipo") == "risposta"}
    attese = {(br, p, i) for p in passate for br in bracci for i in ids}
    mancanti = {p: {br: [i for i in ids if (br, p, i) not in fatte] for br in bracci} for p in passate}
    n_manc = sum(len(x) for d in mancanti.values() for x in d.values())
    errori = [r for r in records if r.get("tipo") == "errore"]
    return {"completo": bool(attese) and n_manc == 0, "attese": len(attese), "registrate": len(fatte & attese),
            "mancanti": n_manc, "passate": passate,
            "passate_complete": [p for p in passate if not any(mancanti[p].values())],
            "mancanti_per_passata": {p: {br: xs for br, xs in d.items() if xs} for p, d in mancanti.items()
                                     if any(d.values())},
            "inattese": [list(x) for x in sorted(fatte - attese)][:20], "errori_registrati": len(errori),
            "ultimi_errori": [str(r.get("messaggio"))[:160] for r in errori[-3:]], "avvisi": avvisi,
            "_chiavi": attese}


def riepilogo(records: list, soglia: float, massimo: int, tetto: float) -> dict:
    comp = completezza(records)
    ultime = {}
    for r in records:  # una sola risposta per (braccio, passata, voce): l'ultima registrata
        if r.get("tipo") == "risposta":
            ultime[(r["braccio"], r["passata"], r["id"])] = r
    chiavi = comp.pop("_chiavi")
    risp = [r for k, r in ultime.items() if k in chiavi]  # le risposte fuori elenco non entrano nei numeri
    jrec = {r["id"]: r for r in records if r.get("tipo") == "j"}
    passate = comp["passate"]
    # passata principale: chat8k SOLO se completa; altrimenti la prima completa (numeri informativi, verdetto INCOMPLETO)
    complete = comp["passate_complete"]
    princ = "chat8k" if "chat8k" in complete else (complete[0] if complete else None)
    out = {"passata_principale": princ, "passate": passate, "soglia": soglia, "massimo": massimo, "tetto_s": tetto,
           "completezza": comp, "j": {}, "bracci": {}, "verdetto": {}}
    for meta in ("taratura", "verifica"):
        out["j"][meta] = misura([(r["oro"], r["scelte"]) for r in jrec.values() if r["meta"] == meta])
    for br in BRACCI:
        b = {"regole": {}, "soglie_taratura": {}, "latenza": {}, "stabilita_fra_passate": None,
             "lettere_top": {}, "nessuna_decisione": 0}
        sel = [r for r in risp if r["braccio"] == br and r["passata"] == princ]
        for meta in ("taratura", "verifica"):
            xs = [r for r in sel if r["meta"] == meta]
            b["regole"][meta] = {
                reg: misura([(r["oro"], regole(r["prob"], r["lettere"], r["nessuna"], r["massa"], soglia, massimo)[reg])
                             for r in xs]) for reg in ("produzione", "r1", "r3")}
        tar = [r for r in sel if r["meta"] == "taratura"]
        for s_ in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
            m = misura([(r["oro"], regole(r["prob"], r["lettere"], r["nessuna"], r["massa"], s_, massimo)["produzione"])
                        for r in tar])
            b["soglie_taratura"][str(s_)] = {k: m[k] for k in ("quota_sbagliate", "quota_su_nessuna", "richiamo", "f1")}
        for p in passate:
            xs = [r for r in risp if r["braccio"] == br and r["passata"] == p]
            lat = [r["lat_s"] for r in xs if r.get("lat_s") is not None]
            tot = [r["tot_s"] for r in xs if r.get("tot_s") is not None]
            b["latenza"][p] = {"n": len(xs), "mediana": BSO.mediana(lat), "p90": BSO.pct(lat, 90),
                               "max": max(lat) if lat else None, "totale_mediana": BSO.mediana(tot),
                               "totale_p90": BSO.pct(tot, 90),
                               "sopra_tetto": sum(1 for t in tot if t > tetto),
                               "quota_sopra_tetto": (sum(1 for t in tot if t > tetto) / len(tot)) if tot else None,
                               "token_prompt_mediana": BSO.mediana([r.get("tokens_evaluated") or 0 for r in xs])}
        if len(passate) > 1:
            a = {r["id"]: r for r in risp if r["braccio"] == br and r["passata"] == passate[0]}
            z = {r["id"]: r for r in risp if r["braccio"] == br and r["passata"] == passate[1]}
            comuni = sorted(set(a) & set(z))
            if comuni:
                uguali = sum(sorted(a[i]["scelte"]["produzione"]) == sorted(z[i]["scelte"]["produzione"]) for i in comuni)
                b["stabilita_fra_passate"] = {"n": len(comuni), "stessa_scelta": uguali / len(comuni)}
        b["lettere_top"] = dict(sorted(Counter(r.get("lettera_top") or "-" for r in sel).items()))
        b["nessuna_decisione"] = sum(1 for r in sel if not r.get("prob") or (r.get("massa") or 0) < S1.MASSA_MINIMA)
        out["bracci"][br] = b
        lat_p = b["latenza"].get(princ) or {}
        out["verdetto"][br] = criteri(b["regole"]["verifica"]["produzione"], out["j"]["verifica"],
                                      lat_p, lat_p.get("quota_sopra_tetto"), princ or "")
        if not comp["completo"]:
            v = out["verdetto"][br]
            v["esito_se_completo"], v["esito"] = v["esito"], "INCOMPLETO"
            v["falliti_parziali"], v["falliti"] = v["falliti"], []  # criteri su dati parziali: solo informativi
            v["nota"] = (f"mancano {comp['mancanti']} risposte su {comp['attese']}: nessun verdetto"
                         + (f"; numeri sulla passata {princ} (completa)" if princ else "; nessuna passata completa"))
    ok = [br for br in BRACCI if out["verdetto"][br]["esito"] == "ACCENDI"]
    if not comp["completo"]:
        out["consiglio"] = (f"INCOMPLETO: mancano {comp['mancanti']} risposte su {comp['attese']} attese "
                            f"(passate incomplete: {', '.join(comp['mancanti_per_passata']) or '-'}): completa il "
                            "registro con --riprendi <file.jsonl>; nessun ACCENDI ne' NON ACCENDERE")
    elif "S" in ok:
        out["consiglio"] = "ACCENDI con 'nessuna' ultima (ODYSSEUS_SKILL_SELETTORE_NESSUNA_PRIMA=0)"
    elif "S'" in ok:
        out["consiglio"] = "ACCENDI con 'nessuna' prima (ODYSSEUS_SKILL_SELETTORE_NESSUNA_PRIMA=1)"
    else:
        out["consiglio"] = ("NON ACCENDERE: riscrivere le description (sulla meta' di taratura) o provare S'; "
                            "mai il ragionamento")
    return out


def stampa_riepilogo(rie: dict, reg) -> None:
    def f(x):
        return "-" if x is None else f"{x:.2f}"
    c = rie["completezza"]
    for a in c["avvisi"]:
        reg.riga(f"avviso: {a}")
    if c["completo"]:
        reg.riga(f"registro completo: {c['registrate']}/{c['attese']} risposte attese (passate {', '.join(c['passate'])}); "
                 f"richieste fallite registrate {c['errori_registrati']} (tutte rifatte)")
    else:
        reg.riga(f"REGISTRO INCOMPLETO: {c['registrate']}/{c['attese']} risposte attese, mancano {c['mancanti']}; "
                 f"richieste fallite registrate {c['errori_registrati']}"
                 + (f" (ultime: {' | '.join(c['ultimi_errori'])})" if c["ultimi_errori"] else ""))
        for p, d in c["mancanti_per_passata"].items():
            for br, xs in d.items():
                reg.riga(f"  mancano [{br} {p}] {len(xs)}: {', '.join(xs[:15])}" + (" ..." if len(xs) > 15 else ""))
    if c["inattese"]:
        reg.riga(f"avviso: risposte fuori dall'elenco atteso (ignorate dalla completezza): {c['inattese'][:5]}")
    mj = rie["j"]["verifica"]
    reg.riga(f"J (verifica): iniezioni {mj['iniezioni']} sbagliate {f(mj['quota_sbagliate'])} su 'nessuna' "
             f"{f(mj['quota_su_nessuna'])} richiamo {f(mj['richiamo'])} F1 {f(mj['f1'])}")
    for br, b in rie["bracci"].items():
        for reg_ in ("produzione", "r1", "r3"):
            m = b["regole"]["verifica"][reg_]
            reg.riga(f"{br:2} {reg_:10} (verifica, n={m['n']}): iniezioni {m['iniezioni']} sbagliate "
                     f"{f(m['quota_sbagliate'])} su 'nessuna' {f(m['quota_su_nessuna'])} richiamo {f(m['richiamo'])} "
                     f"F1 {f(m['f1'])} esatte {f(m['quota_esatte'])}")
        for p, l in b["latenza"].items():
            reg.riga(f"{br:2} latenza {p:6}: mediana {f(l['mediana'])}s p90 {f(l['p90'])}s, totale p90 "
                     f"{f(l['totale_p90'])}s, sopra tetto {l['sopra_tetto']}/{l['n']}")
        reg.riga(f"{br:2} soglie (taratura, produzione): " + "; ".join(
            f"{s}: sb {f(v['quota_sbagliate'])} ne {f(v['quota_su_nessuna'])} ri {f(v['richiamo'])} F1 {f(v['f1'])}"
            for s, v in b["soglie_taratura"].items()))
        v = rie["verdetto"][br]
        reg.riga(f"VERDETTO {br}: {v['esito']}" + (f" (falliti: {', '.join(v['falliti'])})" if v["falliti"] else "")
                 + (f" [{v['nota']}]" if v["nota"] else ""))
    reg.riga(f"CONSIGLIO: {rie['consiglio']}")


# ------------------------------------------------------------------ preparazione comune
def prepara(args) -> dict:
    dataset = Path(args.dataset) if args.dataset else QUI / f"banco-selettore-{args.famiglia}.json"
    if not dataset.exists():
        raise SystemExit(f"dataset assente: {dataset} (v1 esiste solo per il dominio browser)")
    voci, info = carica_dataset(dataset)
    if info.get("dominio") and info["dominio"] != args.famiglia:
        raise SystemExit(f"il dataset e' del dominio {info['dominio']!r}, non {args.famiglia!r}")
    modi = dict(info.get("modi") or MODI_PER_DOMINIO.get(args.famiglia) or {})
    dividi(voci)
    skills, note = carica_skill(cartelle_skill(args), args.owner)
    if not skills:
        raise SystemExit("nessuna skill caricata dalle cartelle indicate")
    paniere = paniere_forzato(modi)
    gestore = gestore_senza_disco()
    t0 = time.perf_counter()
    candidate_di(skills, modi, paniere, voci[0]["testo"], gestore)  # primo giro: import di agent_loop (lento)
    riscaldamento_s = time.perf_counter() - t0
    dom = SEL.domini(modi)
    for v in voci:
        c0 = time.perf_counter()
        cand, tutte = candidate_di(skills, modi, paniere, v["testo"], gestore)
        v["cand_ms"] = (time.perf_counter() - c0) * 1000.0
        v["candidate"] = cand
        v["candidati"] = [s["name"] for s in cand]
        v["tutte"] = [s["name"] for s in tutte]
        v["oro_fuori_prefiltro"] = [o for o in v["oro"] if o in v["tutte"] and o not in v["candidati"]]
        v["oro_mai_candidato"] = [o for o in v["oro"] if o not in v["tutte"]]
        v["j"] = braccio_j(gestore, v["testo"], tutte)
    errori, avvisi = valida(voci, info, {s["name"] for s in skills})
    errori += storico_divisione(args.out, args.famiglia, voci)
    scartate = {s["name"]: perche_scartata(s, dom, paniere) for s in skills
                if not any(s["name"] in v["tutte"] for v in voci)}
    for nome, perche in scartate.items():
        errori.append(f"skill {nome} mai candidata: {perche}")
    if not any(v["candidati"] for v in voci):
        errori.append("zero candidate per tutte le voci: il banco non misurerebbe nulla")
    mai = sorted({o for v in voci for o in v["oro_mai_candidato"]})
    if mai:
        errori.append(f"skill d'oro mai fra le candidate dello stadio 1: {mai}")
    return {"voci": voci, "info": info, "modi": modi, "skills": skills, "note": note, "paniere": paniere,
            "errori": errori, "avvisi": avvisi, "riscaldamento_s": riscaldamento_s, "dataset": dataset}


def intestazione(args, P: dict) -> dict:
    return {"tipo": "intestazione", "quando": dt.datetime.now().isoformat(timespec="seconds"),
            "argomenti": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
            "famiglia": args.famiglia, "modi": P["modi"], "dataset_sha": P["info"]["dataset_sha"],
            "operazioni_sha": P["info"]["operazioni_sha"], "mappa_oro": P["info"]["mappa_oro"],
            "seme": args.seme, "soglia": args.soglia, "massimo": args.massimo, "tetto_s": args.tetto,
            "paniere": sorted(P["paniere"]) if P["paniere"] is not None else None,
            "skills": [{"name": s["name"], "category": s.get("category"), "file": s["_file"], "sha": s["_sha"],
                        "description": s.get("description")} for s in P["skills"]],
            "sistema_sha": sha(S1.SISTEMA), "domanda": SEL.DOMANDA, "opzione_nessuna": SEL.OPZIONE_NESSUNA,
            "j": {"soglia": J_SOGLIA, "max": J_MAX, "min_confidence": J_CONF},
            "divisione": dict(Counter(f"{v['meta']}/{v['classe']}" for v in P["voci"])), "n_voci": len(P["voci"]),
            # meta' di ogni voce: storico contro le fughe fra taratura e verifica nei banchi futuri (storico_divisione)
            "meta_per_id": {v["id"]: v["meta"] for v in P["voci"]},
            "escluse": sorted(P["info"].get("escluse") or {}),
            # cio' che il registro deve contenere per dare un verdetto (riepilogo -> completezza)
            "attese": {"ids": sorted(v["id"] for v in P["voci"] if v["candidati"]), "bracci": list(BRACCI),
                       "passate": [p for p in PASSATE if p in {x.strip() for x in args.passate.split(",")}]}}


def riassunto_dataset(P: dict, reg) -> None:
    voci = P["voci"]
    reg.riga(f"dataset {P['dataset'].name} sha={P['info']['dataset_sha']} (operazioni sha={P['info']['operazioni_sha']}):"
             f" {len(voci)} voci")
    for meta in ("taratura", "verifica"):
        xs = [v for v in voci if v["meta"] == meta]
        c = Counter(v["classe"] for v in xs)
        reg.riga(f"  {meta:9}: {len(xs)} voci, nessuna {c['nessuna']}, una {c['una']}, due {c['due']}; "
                 f"operazioni {sum(v['origine'] != 'scritto' for v in xs)}, scritte {sum(v['origine'] == 'scritto' for v in xs)}")
    c = Counter(v["classe"] for v in voci)
    reg.riga(f"  totale: nessuna {c['nessuna'] / len(voci):.0%}, due skill {c['due'] / len(voci):.0%}; oro per skill: "
             + ", ".join(f"{k}={n}" for k, n in sorted(Counter(o for v in voci for o in v["oro"]).items())))
    fuori = P["info"].get("escluse") or {}
    riscritte = [v["id"] for v in voci if v.get("oro_messaggio")]
    da_hash = [f"{v['id']}={v['meta']}" for v in voci if v.get("meta_da") == "hash"]
    reg.riga(f"  oro dal solo messaggio: {len(riscritte)} formulazioni riscritte ({', '.join(riscritte) or '-'}); "
             f"escluse dal cancello 2: {len(fuori)} ({', '.join(sorted(fuori)) or '-'})")
    reg.riga(f"  meta' dei messaggi scritti: {sum(v.get('meta_da') == 'dataset' for v in voci)} dal campo meta, "
             f"{len(da_hash)} dall'hash dell'id" + (f" ({', '.join(da_hash)})" if da_hash else ""))
    reg.riga(f"skill caricate ({len(P['skills'])}): " + ", ".join(f"{s.get('category')}/{s['name']}" for s in P["skills"]))
    for n in P["note"]:
        reg.riga(f"  nota: {n}")
    reg.riga(f"modi {P['modi']} -> domini {sorted(SEL.domini(P['modi']))}; paniere del modo "
             f"{'non noto offline' if P['paniere'] is None else len(P['paniere'])} strumenti")
    ncand = Counter(len(v["candidati"]) for v in voci)
    reg.riga(f"candidate per voce: {dict(sorted(ncand.items()))} (primo giro con gli import: {P['riscaldamento_s']:.1f}s)")
    persi = [v["id"] for v in voci if v["oro_fuori_prefiltro"]]
    oro_tot = sum(len(v["oro"]) for v in voci)
    reg.riga(f"richiamo del prefiltro lessicale (oltre 8 candidate): "
             f"{1 - sum(len(v['oro_fuori_prefiltro']) for v in voci) / max(1, oro_tot):.2%}"
             + (f", oro perso in {persi[:10]}" if persi else ""))


# ------------------------------------------------------------------ dry-run
def dry_run(args, P: dict, reg) -> int:
    riassunto_dataset(P, reg)
    try:
        mod = BSO.Modello(args.gguf or BSO.gguf_da_config(args.modello))
        tok_ok = mod.codifica("x") is not None
    except (SystemExit, OSError, KeyError) as e:
        mod, tok_ok = None, False
        reg.riga(f"GGUF non leggibile ({e}): token stimati a 3,5 caratteri")
    conta = (lambda t: mod.conta(t)) if tok_ok else (lambda t: int(len(t) / 3.5))
    reg.riga("tokenizzatore: BPE dal GGUF" if tok_ok else "tokenizzatore: stima grezza")
    righe, problemi_lettere, token = [], [], {br: [] for br in BRACCI}
    for v in P["voci"]:
        riga = {"id": v["id"], "meta": v["meta"], "classe": v["classe"], "oro": v["oro"], "testo": v["testo"],
                "etichette": v["etichette"], "oro_messaggio": v.get("oro_messaggio"), "meta_da": v.get("meta_da"),
                "candidati": v["candidati"], "j": v["j"], "cand_ms": round(v["cand_ms"], 2)}
        if v["candidati"]:
            for br, prima in BRACCI.items():
                testi, mappa, nessuna = lettere_di(v["candidate"], prima)
                p = SEL.prompt_selettore(P["modi"], v["testo"], v["candidate"], prima_nessuna=prima)
                n = conta(p)
                token[br].append(n)
                riga[br] = {"lettere": mappa, "nessuna": nessuna, "token": n, "prompt": p,
                            "grammatica": S1.grammatica(len(testi))}
                if tok_ok:
                    base = mod.codifica(p)
                    for L in mappa:
                        ids = mod.codifica(p + L)
                        if not (len(ids) == len(base) + 1 and ids[:-1] == base and ids[-1] in mod.forme_lettera(L)):
                            problemi_lettere.append(f"{v['id']}/{br}:{L}")
        righe.append(riga)
    for br, xs in token.items():
        if xs:
            reg.riga(f"token del prompt {br}: n={len(xs)} min={min(xs)} mediana={int(BSO.mediana(xs))} max={max(xs)}")
    if tok_ok:
        reg.riga("lettere: ogni lettera valida e' UN token dopo </think>" if not problemi_lettere
                 else f"ERRORE lettere non a token singolo: {problemi_lettere[:12]}")
    esempio = S1.payload("<prompt>", 4, args.slot)
    reg.riga(f"payload /completion (system_one.payload): {json.dumps(esempio, ensure_ascii=False)}")
    rie_j = {m: misura([(v["oro"], v["j"]) for v in P["voci"] if v["meta"] == m]) for m in ("taratura", "verifica")}
    for m, x in rie_j.items():
        reg.riga(f"braccio J offline ({m}): iniezioni {x['iniezioni']}, sbagliate {x['quota_sbagliate']:.2f}, "
                 f"su 'nessuna' {x['quota_su_nessuna']:.2f}, richiamo {x['richiamo'] or 0:.2f}, F1 {x['f1']:.2f}")
    for e in P["avvisi"]:
        reg.riga(f"avviso: {e}")
    for e in P["errori"]:
        reg.riga(f"ERRORE: {e}")
    mostra = set(args.mostra.split(",")) if args.mostra else set()
    esempi = [r for r in righe if r["id"] in mostra] if mostra else [r for r in righe if "S" in r][:1]
    for r in esempi:
        for br in BRACCI:
            if br in r:
                print(f"\n===== prompt {br} di {r['id']} (oro {r['oro'] or ['nessuna']}, {r[br]['token']} token, "
                      f"lettere {r[br]['lettere']}) =====")
                print(r[br]["prompt"])
                print("===== fine (qui si legge il token della lettera) =====")
    args.out.mkdir(parents=True, exist_ok=True)
    uscita = args.out / f"dryrun-{args.famiglia}-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    uscita.write_text(json.dumps({
        "intestazione": intestazione(args, P), "tokenizzatore_bpe": tok_ok, "errori": P["errori"],
        "avvisi": P["avvisi"], "problemi_lettere": problemi_lettere, "payload_esempio": esempio,
        "j": rie_j, "escluse": P["info"].get("escluse") or {}, "voci": righe}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    reg.riga(f"dry-run scritto: {uscita}")
    esito = not P["errori"] and not problemi_lettere
    reg.riga("DRY-RUN OK" if esito else "DRY-RUN CON ERRORI")
    return 0 if esito else 1


# ------------------------------------------------------------------ dal vivo
def preflight(srv, args, P: dict, reg) -> dict:
    info = {"tipo": "preflight"}
    try:
        run = srv.running()
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"llama-swap non risponde su {srv.base}: {e}. Avvia lo stack prima (questo script non avvia nulla).")
    modelli = [m.get("model") for m in (run.get("running") or [])]
    info["running"] = modelli
    reg.riga(f"llama-swap: modelli caricati {modelli}")
    if any("uncensored" in str(m) for m in modelli):
        raise SystemExit("caricato un modello uncensored: vietato. Fermati e riferisci.")
    pronto = any(m.get("model") == srv.modello and m.get("state") == "ready" for m in (run.get("running") or []))
    if not pronto:
        # come banco-system-one.py, ma solo /completion: llama-swap carica il profilo alla prima richiesta
        reg.riga(f"carico {srv.modello} con una richiesta di riscaldamento su /completion (non misurata)...")
        srv.completion({"prompt": "ciao", "n_predict": 1, "temperature": 0.0, "id_slot": args.slot,
                        "cache_prompt": False, "stream": False}, timeout=400)
        srv.svuota(args.slot)
    props = srv.props()
    tot = props.get("total_slots")
    info["total_slots"], info["build"] = tot, props.get("build_info")
    reg.riga(f"server: slot totali {tot}, build {props.get('build_info')}, slot del banco {args.slot}")
    if tot is not None and not (0 <= args.slot < int(tot)):
        raise SystemExit(f"slot {args.slot} fuori da 0..{int(tot) - 1}")
    v = next(x for x in P["voci"] if x["candidati"])
    testi, _, _ = lettere_di(v["candidate"], False)
    stato = SEL.stato(P["modi"], v["testo"])
    mio = S1.prompt(stato, SEL.DOMANDA, testi)
    msgs = [{"role": "system", "content": S1.SISTEMA},
            {"role": "user", "content": S1.testo_utente(stato, SEL.DOMANDA, testi)}]
    try:
        srv_p = str(srv.applica_template(msgs).get("prompt", ""))
        srv_p = srv_p[len("<|startoftext|>"):] if srv_p.startswith("<|startoftext|>") else srv_p
        base = srv_p[:-len("<think>")] if srv_p.endswith("<think>") else srv_p
        uguale = bool(base) and mio.startswith(base)
        info["apply_template_prefisso_uguale"] = uguale
        reg.riga(f"/apply-template del server {'UGUALE' if uguale else 'DIVERSO'} dal prompt di system_one (prefisso)")
        if not uguale:
            info["apply_template_server"], info["prompt_system_one"] = srv_p[-400:], mio[-400:]
    except Exception as e:  # noqa: BLE001
        reg.riga(f"/apply-template non disponibile: {e}")
    try:
        toks = srv.tokenizza(mio).get("tokens") or []
        ids = [t if isinstance(t, int) else t.get("id") for t in toks]
        info["tokenize"] = {"n_server": len(ids), "bos_doppio": len(ids) > 1 and ids[0] == ids[1]}
        reg.riga(f"/tokenize: {len(ids)} token (BOS doppio {info['tokenize']['bos_doppio']})")
        if info["tokenize"]["bos_doppio"]:
            raise SystemExit("BOS doppio: il server aggiunge il BOS e il prompt lo contiene gia'. Controllare.")
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        reg.riga(f"/tokenize non disponibile: {e}")
    reg.record(info)
    return info


FRASI_CHAT = (
    "Ho aperto il sito del comune per controllare gli orari dell'anagrafe e le novita' sulla raccolta differenziata.",
    "Poi ho chiesto a Vergilius di riassumere un articolo lungo sulla storia del porto di Genova nel Novecento.",
    "Il riassunto citava le banchine, le gru, gli scioperi del 1960 e il traffico dei container negli anni recenti.",
    "Abbiamo confrontato due tabelle con i passeggeri dei traghetti e calcolato la differenza fra estate e inverno.",
    "Infine ho aperto la pagina del museo del mare per vedere gli orari del sabato e il prezzo del biglietto ridotto.",
)


def chat_finta(conta, obiettivo: int) -> str:
    righe, i = [], 0
    while True:
        righe += [f"Nota {i + k}: {FRASI_CHAT[(i + k) % len(FRASI_CHAT)]}" for k in range(40)]
        i += 40
        testo = "\n".join(righe)
        if conta(testo) >= obiettivo - 60:
            break
    return ("<|im_start|>system\nYou are Vergilius, a local assistant on a Windows PC.<|im_end|>\n"
            "<|im_start|>user\n" + testo + "<|im_end|>\n<|im_start|>assistant\n")


def carica_chat_slot0(srv, conta, args, reg) -> dict:
    p = chat_finta(conta, args.chat_token)
    risp, lat = srv.completion({"prompt": p, "n_predict": 1, "temperature": 0.0, "id_slot": 0,
                                "cache_prompt": True, "stream": False}, timeout=600)
    info = {"tipo": "chat8k", "token_stimati": conta(p), "tokens_evaluated": risp.get("tokens_evaluated"),
            "lat_s": lat, "quando": time.time()}
    reg.record(info)
    reg.riga(f"[chat8k] chat finta ferma nello slot 0: {risp.get('tokens_evaluated')} token in {lat:.1f}s")
    return info


def chiama(srv, args, P: dict, v: dict, braccio: str, passata: str, reg, pos: str) -> dict:
    prima = BRACCI[braccio]
    testi, mappa, nessuna = lettere_di(v["candidate"], prima)
    p = SEL.prompt_selettore(P["modi"], v["testo"], v["candidate"], prima_nessuna=prima)
    risp, lat = srv.completion(S1.payload(p, len(testi), args.slot), timeout=args.timeout)
    t1 = time.perf_counter()
    try:
        srv.svuota(args.slot)  # come system_one.decidi (finally): lo slot del selettore si svuota sempre
        svuota_s = time.perf_counter() - t1
    except Exception as e:  # noqa: BLE001
        svuota_s = None
        reg.riga(f"slot {args.slot} non svuotato: {e}")
    voto = S1.leggi_probabilita(risp, len(testi))
    prob = dict(voto.probabilita) if voto else {}
    massa = voto.massa if voto else None
    sc = regole(prob, mappa, nessuna, massa, args.soglia, args.massimo)
    tot = v["cand_ms"] / 1000.0 + lat + (svuota_s or 0.0)
    tim = risp.get("timings") or {}
    rec = {"tipo": "risposta", "braccio": braccio, "passata": passata, "id": v["id"], "gruppo": v["gruppo"],
           "meta": v["meta"], "classe": v["classe"], "oro": v["oro"], "candidati": v["candidati"],
           "lettere": mappa, "nessuna": nessuna, "prob": prob, "massa": massa,
           "dist": {mappa[L]: round(x, 4) for L, x in prob.items()},
           "lettera_top": voto.lettera if voto else None, "scelte": sc, "lat_s": lat, "svuota_s": svuota_s,
           "cand_ms": round(v["cand_ms"], 3), "tot_s": tot, "sopra_tetto": tot > args.tetto,
           "tokens_evaluated": risp.get("tokens_evaluated"), "tokens_cached": risp.get("tokens_cached"),
           "timings": tim, "id_slot": risp.get("id_slot"), "campionata": risp.get("content"),
           "prompt_sha": sha(p), "quando": time.time()}
    reg.record(rec)
    esito = "OK " if sorted(sc["produzione"]) == sorted(v["oro"]) else "NO "
    reg.riga(f"[{braccio:2} {passata:6}] {pos} {v['id']:7} {v['meta'][:3]} oro={','.join(v['oro']) or 'nessuna'} "
             f"scelte={','.join(sc['produzione']) or 'nessuna'} {esito} top={rec['lettera_top']} "
             f"p={max(prob.values()) if prob else 0:.3f} lat={lat:.3f}s tot={tot:.3f}s prompt={risp.get('tokens_evaluated')}")
    return rec


def dal_vivo(args, P: dict) -> int:
    if P["errori"]:
        for e in P["errori"]:
            print("ERRORE:", e)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    if args.riprendi:
        jsonl = Path(args.riprendi)
        if not jsonl.exists():
            raise SystemExit(f"file da riprendere assente: {jsonl}")
    else:
        etichetta = f"-{args.tag}" if args.tag else ""
        jsonl = args.out / f"selettore-{args.famiglia}{etichetta}-{dt.datetime.now():%Y%m%d-%H%M%S}.jsonl"
    reg = Registro(jsonl.with_suffix(".txt"), jsonl)
    testa = intestazione(args, P)
    fatti, j_fatti = set(), set()
    if args.riprendi:
        vecchi = [json.loads(r) for r in jsonl.read_text(encoding="utf-8").splitlines() if r.strip()]
        prima = next((r for r in vecchi if r.get("tipo") == "intestazione"), None)
        if prima:
            for k in ("dataset_sha", "operazioni_sha", "skills", "soglia", "massimo", "seme", "modi"):
                if prima.get(k) != testa.get(k):
                    raise SystemExit(f"--riprendi: {k} diverso dal banco interrotto (dataset, skill o parametri "
                                     "cambiati): serve un banco nuovo")
            # stesse voci con candidati (lo stadio 1 di produzione puo' cambiare fra un giorno e l'altro)
            if "attese" in prima and (prima["attese"] or {}).get("ids") != testa["attese"]["ids"]:
                raise SystemExit("--riprendi: le voci con candidati sono cambiate dal banco interrotto (codice dello "
                                 "stadio 1 o skill cambiati): serve un banco nuovo")
        fatti = {(r["braccio"], r["passata"], r["id"]) for r in vecchi if r.get("tipo") == "risposta"}
        j_fatti = {r["id"] for r in vecchi if r.get("tipo") == "j"}
        reg.riga(f"ripresa di {jsonl.name}: {len(fatti)} risposte gia' registrate")
        testa["tipo"] = "ripresa"
    if "uncensored" in args.modello.lower() or not S1.modello_ammesso(args.modello):
        raise SystemExit(f"modello {args.modello!r}: il selettore di produzione gira solo su lfm e lfm-vista")
    reg.record(testa)
    riassunto_dataset(P, reg)
    for v in P["voci"]:
        if v["id"] not in j_fatti:
            reg.record({"tipo": "j", "id": v["id"], "meta": v["meta"], "classe": v["classe"], "oro": v["oro"],
                        "candidati": v["tutte"], "scelte": v["j"]})
    srv = crea_server(args.base, args.modello, reg)
    preflight(srv, args, P, reg)
    try:
        mod = BSO.Modello(args.gguf or BSO.gguf_da_config(args.modello))
        conta = mod.conta
    except (SystemExit, OSError, KeyError):
        conta = lambda t: int(len(t) / 3.5)  # noqa: E731
    voci = [v for v in P["voci"] if v["candidati"]]
    random.Random(args.seme).shuffle(voci)
    passate = [p.strip() for p in args.passate.split(",") if p.strip()]
    errori_di_fila = 0
    fallite = []  # richieste di decisione fallite (non consecutive): il registro resta incompleto, --riprendi le rifa'

    def protetto(fn, *a, contesto=None):
        nonlocal errori_di_fila
        try:
            r = fn(*a)
            errori_di_fila = 0
            return r
        except (RuntimeError, OSError, urllib.error.URLError) as e:
            errori_di_fila += 1
            reg.riga(f"ERRORE richiesta{f' {contesto}' if contesto else ''}: {e}")
            reg.record({"tipo": "errore", "messaggio": str(e), "contesto": contesto, "quando": time.time()})
            if contesto:
                fallite.append(contesto)
            if errori_di_fila >= 3:
                raise SystemExit(f"tre errori di fila: banco fermato (riprendi con --riprendi {jsonl})")
            return None

    tot = len(voci) * len(BRACCI)
    for passata in passate:
        mancano = [(v, br) for i, v in enumerate(voci)
                   for br in (list(BRACCI) if i % 2 == 0 else list(reversed(list(BRACCI))))
                   if (br, passata, v["id"]) not in fatti]
        if not mancano:
            reg.riga(f"passata {passata}: gia' completa")
            continue
        reg.riga(f"passata {passata}: {len(mancano)} richieste su {tot}, slot {args.slot}, soglia {args.soglia}, "
                 f"max {args.massimo}, tetto {args.tetto}s")
        protetto(srv.svuota, args.slot)
        protetto(srv.svuota, 0)  # vuoto = nessuna chat nello slot 0; chat8k = solo quella finta
        if passata == "chat8k":
            if protetto(carica_chat_slot0, srv, conta, args, reg) is None:
                raise SystemExit("chat finta nello slot 0 non caricata: passata chat8k non valida")
        # riscaldamento non misurato (primo prompt a freddo)
        v0 = mancano[0][0]
        t0, _, _ = lettere_di(v0["candidate"], False)
        protetto(srv.completion, S1.payload(SEL.prompt_selettore(P["modi"], v0["testo"], v0["candidate"]),
                                            len(t0), args.slot), args.timeout)
        protetto(srv.svuota, args.slot)
        try:
            for k, (v, br) in enumerate(mancano, 1):
                protetto(chiama, srv, args, P, v, br, passata, reg, f"{k:03d}/{len(mancano):03d}",
                         contesto=f"{br}/{passata}/{v['id']}")
        finally:
            if passata == "chat8k":
                try:
                    srv.svuota(0)
                    reg.riga("[chat8k] slot 0 svuotato")
                except Exception as e:  # noqa: BLE001
                    reg.riga(f"[chat8k] slot 0 NON svuotato: {e} (svuotarlo a mano: /upstream/{args.modello}/slots/0?action=erase)")
    if fallite:
        reg.riga(f"richieste fallite in questa sessione: {len(fallite)} ({', '.join(fallite[:10])}"
                 f"{' ...' if len(fallite) > 10 else ''}): registro incompleto, rifalle con --riprendi {jsonl}")
    return chiudi(jsonl, args, reg)


def chiudi(jsonl: Path, args, reg) -> int:
    records = [json.loads(r) for r in jsonl.read_text(encoding="utf-8").splitlines() if r.strip()]
    testa = next((r for r in records if r.get("tipo") == "intestazione"), {})
    soglia = testa.get("soglia", args.soglia)
    massimo = testa.get("massimo", args.massimo)
    tetto = testa.get("tetto_s", args.tetto)
    rie = riepilogo(records, soglia, massimo, tetto)
    rie["famiglia"], rie["modi"] = testa.get("famiglia"), testa.get("modi")  # numeri per modo
    rie["file_grezzi"] = str(jsonl)
    uscita = jsonl.with_name(jsonl.stem + "-riepilogo.json")
    uscita.write_text(json.dumps(rie, ensure_ascii=False, indent=1), encoding="utf-8")
    stampa_riepilogo(rie, reg)
    reg.riga(f"riepilogo scritto: {uscita}")
    if not rie["completezza"]["completo"]:
        reg.riga(f"ESITO INCOMPLETO: completa il registro con --riprendi {jsonl}")
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Banco del selettore delle skill (cancello 2 della biblioteca)")
    ap.add_argument("--famiglia", required=True, help="dominio della biblioteca (biblioteca-skill\\<dominio>), es. browser")
    ap.add_argument("--skill-dir", action="append", default=[],
                    help="cartella di skill in piu' (staging); ripetibile; stesso nome = sostituisce la biblioteca")
    ap.add_argument("--senza-biblioteca", action="store_true", help="solo le cartelle --skill-dir")
    ap.add_argument("--dataset", default=None, help="predefinito: banco-selettore-<famiglia>.json accanto allo script")
    ap.add_argument("--owner", default="admin", help="proprietario delle skill visto in produzione ('' = nessun filtro)")
    ap.add_argument("--seme", type=int, default=SEME,
                    help="seme dell'ordine delle richieste (la divisione taratura/verifica non dipende piu' dal seme)")
    ap.add_argument("--dry-run", action="store_true", help="niente rete: valida il dataset e rende i prompt")
    ap.add_argument("--riprendi", default=None, help="jsonl di un banco interrotto da completare")
    ap.add_argument("--riepiloga", default=None, help="jsonl gia' scritto: rifa' metriche e verdetto (offline)")
    ap.add_argument("--passate", default=",".join(PASSATE), help="fra vuoto e chat8k (chat finta nello slot 0)")
    ap.add_argument("--base", default="http://127.0.0.1:8012", help="indirizzo di llama-swap")
    ap.add_argument("--modello", default="lfm", help="profilo di llama-swap (solo lfm o lfm-vista; mai uncensored)")
    ap.add_argument("--gguf", default=None, help="GGUF per il conteggio dei token (predefinito: llama-swap/config.yaml)")
    ap.add_argument("--slot", type=int, default=SEL.SLOT_PREDEFINITO, help="slot fisso delle decisioni (mai 0 ne' 3)")
    ap.add_argument("--soglia", type=float, default=SEL.soglia(), help="massa della regola di produzione")
    ap.add_argument("--massimo", type=int, default=SEL.massimo(), help="skill al massimo per turno")
    ap.add_argument("--tetto", type=float, default=SEL.tetto(), help="tetto in secondi (candidati + richiesta + svuotamento)")
    ap.add_argument("--timeout", type=float, default=30.0, help="timeout di una richiesta (il banco misura oltre il tetto)")
    ap.add_argument("--chat-token", type=int, default=CHAT_TOKEN, help="token della chat finta della passata chat8k")
    ap.add_argument("--tag", default="", help="etichetta nel nome dei file")
    ap.add_argument("--out", type=Path, default=MISURE)
    ap.add_argument("--mostra", default=None, help="dry-run: id delle voci da stampare per intero (es. A04-d,M19)")
    args = ap.parse_args(argv)
    if "uncensored" in args.modello.lower():
        raise SystemExit("lfm-uncensored e' vietato in questo banco")
    if args.slot in SLOT_VIETATI:
        raise SystemExit("slot 0 (chat) e 3 (servizi, Odysseus lo svuota) vietati per le decisioni del banco")
    if args.slot == S1.slot():
        print(f"attenzione: lo slot {args.slot} e' quello del decisore del prefetch (system_one.slot())", flush=True)
    bad = [p for p in args.passate.split(",") if p.strip() and p.strip() not in PASSATE]
    if bad:
        raise SystemExit(f"passate sconosciute: {bad}")
    if args.riepiloga:
        jsonl = Path(args.riepiloga)
        return chiudi(jsonl, args, Registro(None, None))
    P = prepara(args)
    if args.dry_run:
        return dry_run(args, P, Registro(None, None))
    return dal_vivo(args, P)


if __name__ == "__main__":
    sys.exit(main())
