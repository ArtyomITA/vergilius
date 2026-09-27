"""Prototipo del controllo qualita' delle skill (stanza 3, BIBLIOTECARIO). Sola lettura.

Uso: odysseus\\venv\\Scripts\\python.exe scripts\\verifica-skill.py [--operazioni-verifica FILE.json]
     <file SKILL.md o cartelle o .md con blocchi ```markdown>
--operazioni-verifica: la regex atteso.segreto_re di ogni operazione con ruolo "verifica" non deve
comparire nel testo della skill (cancello 1 dello sciame, stessa regola di banco-browser.py --contaminazione).
Controlla ogni skill contro gli SCHEMI VERI degli strumenti (import in sola lettura dal repo) e
conta i token con il vocabolario di LFM2.5 letto dal GGUF. Esce 1 se c'e' almeno un ERRORE.
"""
import atexit, json, os, re, shutil, sys, tempfile

# Importare `services` apre il database di Odysseus e lo tocca (app.db): il controllo delle skill e' in sola
# lettura, quindi gira su una cartella dati temporanea, cancellata alla fine (come banco-selettore-skill.py).
if not os.environ.get("ODYSSEUS_DATA_DIR"):
    _DATA_TEMPORANEA = tempfile.mkdtemp(prefix="verifica-skill-data-")
    os.environ["ODYSSEUS_DATA_DIR"] = _DATA_TEMPORANEA
    atexit.register(shutil.rmtree, _DATA_TEMPORANEA, ignore_errors=True)

from pathlib import Path
REPO =os.environ.get("VERGILIUS_ODYSSEUS_DIR") or str(Path(__file__).resolve().parents[1] / "odysseus")
sys.path.insert(0, REPO)
sys.stdout.reconfigure(encoding="utf-8")

from services.memory.skill_format import Skill, parse_frontmatter  # noqa: E402

# ---- schemi veri --------------------------------------------------------------------------
SCHEMI = {}
def _carica(mod, attr):
    try:
        m = __import__(mod, fromlist=[attr])
        for s in getattr(m, attr):
            f = s.get("function", s)
            SCHEMI[f["name"]] = f.get("parameters") or {}
    except Exception as exc:  # modulo non importabile: lo si dice, non si inventa
        print(f"[avviso] schemi da {mod}.{attr} non caricati: {exc!r}")
_carica("src.agent_tools.browser_tools", "BROWSER_TOOL_SCHEMAS")
_carica("src.shadowbroker.schemi", "OSINT_TOOL_SCHEMAS")
_carica("src.shadowbroker.schemi", "FINANCE_TOOL_SCHEMAS")
_carica("src.agent_tools.calc_tools", "CALC_TOOL_SCHEMAS")
_carica("src.tool_schemas", "FUNCTION_TOOL_SCHEMAS")
NOMI = set(SCHEMI)
PREFISSI_VIETATI = ("browser", "osint", "fin-", "fin_", "web", "manage", "calcola", "mcp")

# ---- token LFM2.5 -------------------------------------------------------------------------
def _tokenizer():
    from gguf import GGUFReader
    from tokenizers import Tokenizer, models, pre_tokenizers
    r = GGUFReader(os.environ.get("VERGILIUS_LFM_GGUF") or r"C:/vergilius-build/models/LFM2.5-2.6B-Q8_0.gguf")
    def _s(n):
        f = r.fields[n]
        return [bytes(f.parts[i]).decode("utf-8", "replace") for i in f.data]
    vocab = {t: i for i, t in enumerate(_s("tokenizer.ggml.tokens"))}
    merges = [tuple(m.split(" ", 1)) for m in _s("tokenizer.ggml.merges")]
    tok = Tokenizer(models.BPE(vocab=vocab, merges=merges))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    return lambda t: len(tok.encode(t).ids)
try:
    NTOK = _tokenizer()
except Exception as exc:
    print(f"[avviso] tokenizzatore GGUF non disponibile ({exc!r}): stima 1 token ogni 3,5 caratteri")
    NTOK = lambda t: int(len(t) / 3.5) + 1

# ---- resa come la vedra' il modello (header proposto dal SELETTORE, senza nome) ------------
def resa(sk: Skill) -> str:
    righe = [f"### Procedure (guidance, not a tool): {sk.description}"]
    if sk.when_to_use:
        righe.append(f"_When to use:_ {sk.when_to_use}")
    if sk.procedure:
        righe.append("Procedure:")
        righe += [f"  {i}. {p}" for i, p in enumerate(sk.procedure, 1)]
    if sk.pitfalls:
        righe.append("Pitfalls: " + "; ".join(sk.pitfalls))
    return "\n".join(righe)

# ---- chiamate citate nel testo: nome_strumento {json} --------------------------------------
def _oggetto(testo, i):
    """Da testo[i]=='{' restituisce la sottostringa bilanciata, o None."""
    prof, in_str = 0, False
    for j in range(i, len(testo)):
        c = testo[j]
        if c == '"' and testo[j - 1] != "\\":
            in_str = not in_str
        elif not in_str and c == "{":
            prof += 1
        elif not in_str and c == "}":
            prof -= 1
            if prof == 0:
                return testo[i:j + 1]
    return None

def chiamate(testo):
    out = []
    for m in re.finditer(r"\b([a-z][a-z0-9_]*)\s*\{", testo):
        blob = _oggetto(testo, m.end() - 1)
        if blob:
            out.append((m.group(1), blob))
    # oggetti JSON senza nome di strumento davanti (argomenti "orfani")
    orfani = []
    for m in re.finditer(r'(?<![a-z_ ])\s\{"', testo):
        blob = _oggetto(testo, m.start() + 1)
        if blob and not any(blob == b for _, b in out):
            orfani.append(blob)
    return out, orfani

def _json(blob):
    # segnaposto <...> non fra virgolette -> 0, per poter controllare le chiavi
    return json.loads(re.sub(r"(?<=[:\[,])\s*<[^<>\"]*>", "0", blob))

def controlla(sk: Skill, fm: dict, dove: str):
    err, avv = [], []
    iniettato = resa(sk)
    n_inj, n_desc = NTOK(iniettato), NTOK(sk.description)
    # nome e descrizione (bug del Mar Nero)
    if "_" in sk.name or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+){1,5}", sk.name):
        err.append(f"nome '{sk.name}': serve kebab-case di 2-6 parole, niente '_'")
    if sk.name in NOMI or sk.name.replace("-", "_") in NOMI or sk.name.startswith(PREFISSI_VIETATI):
        err.append(f"nome '{sk.name}' sembra uno strumento")
    # la marca "non e' uno strumento" sta nella resa (intestazione), non in ogni descrizione:
    # nelle 8 opzioni del selettore un prefisso uguale per tutte e' solo rumore
    if re.match(r"(?i)(procedura|procedure)[, ]+no", sk.description):
        avv.append("descrizione: togli il prefisso 'Procedura, non uno strumento': lo mette la resa")
    if re.search(r"(the|and|with|when)", sk.description):
        avv.append("descrizione in inglese? il selettore legge opzioni in italiano")
    if n_desc > 25:
        err.append(f"descrizione {n_desc} token (tetto 25)")
    # provenienza
    if sk.source != "user":
        err.append(f"source '{sk.source}': le skill della biblioteca sono 'user'")
    if sk.owner != "admin":
        avv.append(f"owner '{sk.owner}' (atteso admin)")
    if sk.status != "published":
        err.append(f"status '{sk.status}'")
    # forma
    if sk.verification:
        err.append("## Verification non arriva al modello: spostala come ultimo passo 'Check:' di Procedure")
    if sk.body_extra.strip():
        err.append("testo fuori dalle 4 sezioni (body_extra): non arriva al modello")
    if not sk.when_to_use:
        err.append("manca ## When to Use")
    if not (3 <= len(sk.procedure) <= 7):
        err.append(f"Procedure con {len(sk.procedure)} passi (3-7)")
    elif not sk.procedure[-1].startswith("Check:"):
        err.append("ultimo passo di Procedure deve cominciare con 'Check:'")
    if len(sk.pitfalls) > 3:
        err.append(f"Pitfalls {len(sk.pitfalls)} voci (max 3, finiscono su una riga)")
    if n_inj > 300:
        err.append(f"parte iniettata {n_inj} token (tetto 300)")
    # strumenti e parametri contro gli schemi veri
    testo = "\n".join(sk.procedure + sk.pitfalls + [sk.when_to_use])
    trovate, orfani = chiamate(testo)
    citati = set()
    for nome, blob in trovate:
        if nome not in SCHEMI:
            if "_" not in nome:
                continue  # parola inglese davanti a un oggetto ("or {...}"), non un nome di strumento
            err.append(f"strumento inesistente: {nome} {blob}")
            continue
        citati.add(nome)
        try:
            args = _json(blob)
        except Exception as exc:
            err.append(f"JSON non valido per {nome}: {blob} ({exc})")
            continue
        props = (SCHEMI[nome].get("properties") or {})
        req = SCHEMI[nome].get("required") or []
        for k, v in args.items():
            if k not in props:
                err.append(f"{nome}: parametro '{k}' non esiste nello schema (validi: {sorted(props)})")
            elif "enum" in props[k] and isinstance(v, str) and not v.startswith("<") and v not in props[k]["enum"]:
                err.append(f"{nome}: {k}='{v}' fuori enum {props[k]['enum']}")
        mancano = [r for r in req if r not in args]
        if mancano:
            err.append(f"{nome}: mancano obbligatori {mancano} in {blob}")
    for blob in orfani:
        avv.append(f"argomenti senza nome di strumento davanti: {blob}")
    # nomi di strumento citati senza argomenti
    for nome in NOMI:
        if re.search(rf"\b{re.escape(nome)}\b", testo):
            citati.add(nome)
    dichiarati = set(fm.get("tools") or [])
    if not dichiarati:
        err.append("manca il campo tools: [..] (serve al selettore per il filtro sul paniere)")
    else:
        if dichiarati - NOMI:
            err.append(f"tools: nomi inesistenti {sorted(dichiarati - NOMI)}")
        if citati - dichiarati:
            avv.append(f"strumenti citati ma non in tools: {sorted(citati - dichiarati)}")
    return n_inj, n_desc, err, avv

def skill_da(percorso):
    testo = open(percorso, encoding="utf-8").read()
    if testo.lstrip().startswith("---"):
        return [(percorso, testo)]
    return [(f"{percorso}#{i}", b) for i, b in enumerate(re.findall(r"```markdown\n(.*?)\n```", testo, re.S), 1)]

def segreti_di_verifica(percorso):
    dati = json.load(open(percorso, encoding="utf-8"))
    ops = dati.get("operazioni", dati) if isinstance(dati, dict) else dati
    out = []
    for o in ops:
        rx = (o.get("atteso") or {}).get("segreto_re")
        if o.get("ruolo") == "verifica" and rx:
            out.append((o.get("id", "?"), re.compile(rx, re.I)))
    return out


def contaminazione(sk: Skill, segreti):
    testo = "\n".join([sk.description, " ".join(sk.tags or []), sk.when_to_use or ""] + sk.procedure + sk.pitfalls)
    return [f"contaminata dall'operazione di verifica {oid}: '{m.group(0)}'"
            for oid, rx in segreti for m in [rx.search(testo)] if m]


def main(argv):
    file = []
    segreti = []
    if "--operazioni-verifica" in argv:
        i = argv.index("--operazioni-verifica")
        segreti = segreti_di_verifica(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
        print(f"operazioni di verifica con segreto_re: {len(segreti)}")
    for a in argv:
        if os.path.isdir(a):
            for r, _, fs in os.walk(a):
                file += [os.path.join(r, f) for f in fs if f == "SKILL.md"]
        else:
            file.append(a)
    print(f"schemi caricati: {len(SCHEMI)} strumenti")
    errori = 0
    for f in file:
        for dove, testo in skill_da(f):
            fm, _ = parse_frontmatter(testo)
            sk = Skill.from_markdown(testo)
            n_inj, n_desc, err, avv = controlla(sk, fm, dove)
            err += contaminazione(sk, segreti)
            esito = "OK " if not err else "ERR"
            print(f"\n{esito} {sk.name}  iniettato={n_inj} tok  descrizione={n_desc} tok  [{dove}]")
            for e in err:
                print(f"   ERRORE  {e}")
            for a in avv:
                print(f"   avviso  {a}")
            errori += bool(err)
    print(f"\nskill con errori: {errori}")
    return 1 if errori else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
