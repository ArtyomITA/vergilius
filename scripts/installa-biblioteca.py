"""Installa in Odysseus le skill della biblioteca che hanno superato il banco (stanza 3, 27 set 2026).

Uso: odysseus\\venv\\Scripts\\python.exe scripts\\installa-biblioteca.py [--prova]
     odysseus\\venv\\Scripts\\python.exe scripts\\installa-biblioteca.py --prova-famiglia DOMINIO [--operazioni FILE] [--prova]
     odysseus\\venv\\Scripts\\python.exe scripts\\installa-biblioteca.py --togli-prova [--tieni-cambiate] [--prova]
     --dest CARTELLA al posto di odysseus\\data\\skills (prove offline), --manifesto FILE al posto di
     biblioteca-skill\\.prova-in-corso.json

Contaminazione (cancello 1): ogni skill si controlla contro le operazioni di VERIFICA del SUO dominio,
scripts\\operazioni-<dominio>.json (--operazioni FILE con --prova-famiglia). Se il file del dominio manca, la skill
non passa: mai il ripiego silenzioso sulle operazioni del browser.

Regole del piano chiuso (PLAN v4, obiettivo 4):
- sorgenti in biblioteca-skill\\<dominio>\\<nome>\\SKILL.md (versionate), PROVE.md accanto e MAI installato;
- si copia una skill SOLO se il suo nome e' in biblioteca-skill\\INSTALLATE.txt (lo aggiunge il LEAD dopo il
  verdetto TIENI del banco A-B-B-A) E se scripts\\verifica-skill.py le da' zero errori;
- destinazione odysseus\\data\\skills\\<category>\\<name>\\SKILL.md; rieseguirlo ripristina le skill che il modello
  avesse modificato con manage_skills.
--prova: dice cosa farebbe, senza scrivere (vale anche con --prova-famiglia e --togli-prova).

Prova di famiglia (cancello 3, emendamento del proprietario del 27 set):
--prova-famiglia DOMINIO: installa TUTTE le skill di biblioteca-skill\\<DOMINIO> che passano il cancello 1
  (verifica-skill.py a zero errori, una sola chiamata per tutta la famiglia), anche fuori da INSTALLATE.txt, per
  banco-browser.py --ab-famiglia DOMINIO. Scrive il manifesto biblioteca-skill\\.prova-in-corso.json (file copiati con
  sha256, cartelle create) man mano che copia. Non sovrascrive MAI: una skill con lo stesso nome gia' in data/skills
  e con un testo diverso (di altri, o della biblioteca ma modificata) ferma tutto PRIMA di copiare. Una gia' presente
  identica resta dov'e', registrata come "gia' presente": --togli-prova non la tocca.
--togli-prova: rimuove esattamente i file copiati elencati nel manifesto (mai altri), poi le cartelle che la prova
  aveva creato se sono rimaste vuote, poi il manifesto. Una skill entrata nel frattempo in INSTALLATE.txt resta.
  Un file copiato e poi RISCRITTO da altri durante la prova (sha256 diverso: manage_skills, la UI del proprietario)
  non si tocca: resta con la sua cartella, il manifesto resta, uscita 3. Si decide a mano: cancellarlo e rilanciare
  --togli-prova, oppure --togli-prova --tieni-cambiate (resta dov'e' e non e' piu' della prova).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
BIBLIOTECA = RADICE / "biblioteca-skill"
ELENCO = BIBLIOTECA / "INSTALLATE.txt"
MANIFESTO = BIBLIOTECA / ".prova-in-corso.json"
DESTINAZIONE = RADICE / "odysseus" / "data" / "skills"
PYTHON = RADICE / "odysseus" / "venv" / "Scripts" / "python.exe"
VERIFICA = RADICE / "scripts" / "verifica-skill.py"


def operazioni_di(dominio: str) -> Path:
    """Operazioni di verifica del dominio (segreto_re contro la contaminazione): una per famiglia."""
    return RADICE / "scripts" / f"operazioni-{dominio}.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def nomi_ammessi() -> list[str]:
    if not ELENCO.exists():
        return []
    righe = ELENCO.read_text(encoding="utf-8").splitlines()
    return [r.strip() for r in righe if r.strip() and not r.lstrip().startswith("#")]


def sorgenti() -> dict[str, Path]:
    out = {}
    for skill in BIBLIOTECA.glob("*/*/SKILL.md"):
        out[skill.parent.name] = skill
    return out


def _frontmatter(skill: Path, chiave: str) -> str:
    for riga in skill.read_text(encoding="utf-8").splitlines()[1:40]:
        if riga.startswith(f"{chiave}:"):
            return riga.split(":", 1)[1].strip().strip('"')
        if riga.strip() == "---":
            break
    return ""


def categoria(skill: Path) -> str:
    return _frontmatter(skill, "category") or skill.parent.parent.name


def sha256(percorso: Path) -> str:
    return hashlib.sha256(percorso.read_bytes()).hexdigest()


def _esegui_verifica(cmd: list) -> subprocess.CompletedProcess:
    """verifica-skill.py importa services/ di odysseus, che crea e scrive app.db in DATA_DIR: gli si da' una DATA
    temporanea (gli schemi degli strumenti sono costanti dei moduli, non dipendono da DATA_DIR)."""
    with tempfile.TemporaryDirectory(prefix="verifica-skill-data-", ignore_cleanup_errors=True) as tmp:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=dict(os.environ, ODYSSEUS_DATA_DIR=tmp))


def verifica(skill: Path, operazioni: Path) -> bool:
    cmd = [str(PYTHON), str(VERIFICA), "--operazioni-verifica", str(operazioni), str(skill)]
    esito = _esegui_verifica(cmd)
    if esito.returncode != 0:
        print(esito.stdout[-1500:])
    return esito.returncode == 0


def verifica_molte(skill: list[Path], operazioni: Path) -> dict[str, list]:
    """Cancello 1 in UNA chiamata di verifica-skill.py per tutta la famiglia (schemi e GGUF costano ~50 s a
    chiamata), contaminazione contro le operazioni di verifica della famiglia. Esito per file:
    {percorso risolto: [ok, righe ERRORE]}; un file senza riga d'esito = non passato."""
    cmd = [str(PYTHON), str(VERIFICA), "--operazioni-verifica", str(operazioni)]
    cmd += [str(s) for s in skill]
    esito = _esegui_verifica(cmd)
    if esito.returncode not in (0, 1):
        print(esito.stdout[-1500:], esito.stderr[-1500:])
        raise SystemExit(f"verifica-skill.py e' uscito con {esito.returncode}: niente da installare")
    out, corrente = {}, None
    for riga in esito.stdout.splitlines():
        m = re.match(r"^(OK |ERR) (\S+)\s+iniettato=.*\[(.+)\]\s*$", riga)
        if m:
            corrente = str(Path(m.group(3)).resolve())
            out[corrente] = [m.group(1) == "OK ", []]
        elif corrente and riga.strip().startswith("ERRORE"):
            out[corrente][1].append(riga.strip())
    return out


# ------------------------------------------------------------------ installazione normale (INSTALLATE.txt)
def installa_elenco(dest: Path, prova: bool) -> int:
    ammessi = nomi_ammessi()
    disponibili = sorgenti()
    if not ammessi:
        print("INSTALLATE.txt vuoto: nessuna skill ha ancora il verdetto TIENI, niente da installare.")
        return 0
    errori = 0
    for nome in ammessi:
        skill = disponibili.get(nome)
        if skill is None:
            print(f"[manca] {nome}: non c'e' in biblioteca-skill")
            errori += 1
            continue
        ops = operazioni_di(skill.parent.parent.name)
        if not ops.exists():
            print(f"[scartata] {nome}: manca {ops} (operazioni di verifica del dominio {skill.parent.parent.name}): "
                  "senza, la contaminazione non si controlla")
            errori += 1
            continue
        if not verifica(skill, ops):
            print(f"[scartata] {nome}: verifica-skill.py ha trovato errori")
            errori += 1
            continue
        dst = dest / categoria(skill) / nome / "SKILL.md"
        if prova:
            print(f"[prova] {skill} -> {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill, dst)
        print(f"[installata] {nome} -> {dst}")
    return 1 if errori else 0


# ------------------------------------------------------------------ prova di famiglia (cancello 3)
def _scrivi(manifesto: Path, dati: dict) -> None:
    tmp = manifesto.with_name(manifesto.name + ".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(manifesto)


def _crea_cartelle(cartella: Path, create: list) -> None:
    """mkdir di tutta la catena mancante, registrando ogni cartella creata (per toglierla dopo, se vuota)."""
    mancanti = []
    p = cartella
    while not p.exists():
        mancanti.append(p)
        p = p.parent
    for c in reversed(mancanti):
        c.mkdir()
        create.append(str(c))


def prova_famiglia(dominio: str, dest: Path, manifesto: Path, prova: bool, operazioni: Path | None = None) -> int:
    if manifesto.exists():
        print(f"[ferma] c'e' gia' una prova in corso ({manifesto}): prima --togli-prova")
        return 2
    cartella = BIBLIOTECA / dominio
    skill = sorted(cartella.glob("*/SKILL.md"))
    if not skill:
        print(f"[ferma] nessuna skill in {cartella}")
        return 1
    ops = operazioni or operazioni_di(dominio)
    if not ops.exists():
        print(f"[ferma] operazioni di verifica della famiglia {dominio} assenti ({ops}): il cancello 1 non puo' "
              "controllare la contaminazione. Scrivi il file del dominio o passa --operazioni FILE")
        return 2
    print(f"cancello 1 su {len(skill)} skill di {dominio} (verifica-skill.py, una chiamata; contaminazione contro "
          f"{ops.name})...", flush=True)
    esiti = verifica_molte(skill, ops)
    passate, scartate = [], []
    for s in skill:
        ok, err = esiti.get(str(s.resolve()), [False, ["verifica-skill.py non ha dato esito per questo file"]])
        nome_file = _frontmatter(s, "name")
        if ok and nome_file != s.parent.name:
            ok, err = False, [f"name '{nome_file}' diverso dalla cartella '{s.parent.name}'"]
        (passate if ok else scartate).append((s, err))
    for s, err in scartate:
        print(f"[scartata] {s.parent.name}: " + ("; ".join(err) or "errori del cancello 1"))
    installate = set(nomi_ammessi())
    piano, gia, conflitti = [], [], []
    for s, _ in passate:
        nome = s.parent.name
        dst = dest / categoria(s) / nome / "SKILL.md"
        esistenti = sorted(dest.glob(f"*/{nome}/SKILL.md")) if dest.exists() else []
        if not esistenti:
            piano.append((s, dst))
        elif esistenti == [dst] and sha256(dst) == sha256(s):
            gia.append((s, dst))
        else:
            perche = ("e' in INSTALLATE.txt ma il testo installato e' diverso (modificata con manage_skills?): "
                      "rilancia installa-biblioteca.py senza opzioni per ripristinarla, poi riprova"
                      if nome in installate else
                      "una skill con questo nome che non viene dalla biblioteca (o e' in un'altra categoria): "
                      "non la sovrascrivo")
            conflitti.append(f"{nome}: {', '.join(str(e) for e in esistenti)}: {perche}")
    if conflitti:
        for c in conflitti:
            print(f"[ferma] {c}")
        print("niente copiato: risolvi i conflitti a mano e riprova.")
        return 2
    if not piano and not gia:
        print("nessuna skill della famiglia passa il cancello 1: niente da provare")
        return 1
    for s, dst in gia:
        print(f"[gia' presente] {s.parent.name} -> {dst} (identica: resta, --togli-prova non la tocca)")
    if prova:
        for s, dst in piano:
            print(f"[prova] {s} -> {dst}")
        print(f"[prova] manifesto {manifesto}")
        return 0
    dati = {"famiglia": dominio, "creato": dt.datetime.now().isoformat(timespec="seconds"),
            "dest": str(dest.resolve()), "operazioni_verifica": str(ops.resolve()), "copiate": [],
            "gia_presenti": [{"nome": s.parent.name, "file": str(d)} for s, d in gia],
            "scartate": [{"nome": s.parent.name, "errori": e} for s, e in scartate],
            "cartelle_create": []}
    _scrivi(manifesto, dati)
    for s, dst in piano:
        _crea_cartelle(dst.parent, dati["cartelle_create"])
        shutil.copyfile(s, dst)
        dati["copiate"].append({"nome": s.parent.name, "sorgente": str(s), "file": str(dst), "sha256": sha256(dst)})
        _scrivi(manifesto, dati)
        print(f"[prova installata] {s.parent.name} -> {dst}")
    print(f"manifesto: {manifesto} ({len(dati['copiate'])} copiate, {len(gia)} gia' presenti, "
          f"{len(scartate)} scartate dal cancello 1)")
    return 0


def togli_prova(dest: Path | None, manifesto: Path, prova: bool, tieni_cambiate: bool = False) -> int:
    if not manifesto.exists():
        print(f"nessuna prova in corso ({manifesto} assente): niente da togliere")
        return 0
    dati = json.loads(manifesto.read_text(encoding="utf-8"))
    radice = Path(dati["dest"]).resolve()
    if dest is not None and dest.resolve() != radice:
        print(f"[ferma] il manifesto e' di {radice}, non di {dest.resolve()}")
        return 2
    installate = set(nomi_ammessi())
    cambiate = []
    for x in dati.get("copiate", []):
        f = Path(x["file"])
        if f.resolve().parent.parent.parent != radice or f.name != "SKILL.md":
            print(f"[salto] {f}: fuori da {radice} o non e' un SKILL.md (manifesto alterato?)")
            continue
        if x["nome"] in installate:
            print(f"[resta] {x['nome']}: ora e' in INSTALLATE.txt (installazione vera)")
            continue
        if not f.exists():
            print(f"[gia' tolta] {f}")
            continue
        if sha256(f) != x.get("sha256"):
            # il contenuto non e' piu' quello copiato dalla prova (manage_skills, UI del proprietario): mai cancellarlo
            if tieni_cambiate:
                print(f"[resta] {f}: cambiata durante la prova, la tieni (--tieni-cambiate): non e' piu' della prova")
            else:
                print(f"[resta] {f}: cambiata durante la prova (manage_skills o la UI?): non la tolgo, controlla a mano")
                cambiate.append(str(f))
            continue
        if prova:
            print(f"[prova] tolgo {f}")
            continue
        f.unlink()
        print(f"[tolta] {f}")
    for c in reversed(dati.get("cartelle_create", [])):
        p = Path(c)
        if p.is_dir() and not any(p.iterdir()):
            if prova:
                print(f"[prova] tolgo la cartella vuota {p}")
                continue
            p.rmdir()
    if cambiate:
        print(f"[ferma] {len(cambiate)} file riscritti durante la prova restano, e resta il manifesto {manifesto}. "
              "Decidi a mano: cancellali e rilancia --togli-prova, oppure --togli-prova --tieni-cambiate per tenerli "
              "(escono dalla prova)")
        return 3
    if prova:
        print(f"[prova] tolgo il manifesto {manifesto}")
        return 0
    manifesto.unlink()
    print(f"prova della famiglia {dati.get('famiglia')} tolta; manifesto rimosso")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Installatore della biblioteca di skill")
    ap.add_argument("--prova", action="store_true", help="dice cosa farebbe, senza scrivere")
    ap.add_argument("--prova-famiglia", metavar="DOMINIO", default="",
                    help="installa per l'A/B tutte le skill del dominio che passano il cancello 1")
    ap.add_argument("--togli-prova", action="store_true", help="toglie esattamente cio' che la prova ha copiato")
    ap.add_argument("--dest", type=Path, default=None, help="al posto di odysseus\\data\\skills (prove offline)")
    ap.add_argument("--manifesto", type=Path, default=MANIFESTO)
    ap.add_argument("--operazioni", type=Path, default=None,
                    help="con --prova-famiglia: operazioni di verifica della famiglia per la contaminazione "
                         "(predefinito scripts\\operazioni-DOMINIO.json; se manca, la prova si ferma)")
    ap.add_argument("--tieni-cambiate", action="store_true",
                    help="con --togli-prova: i file riscritti durante la prova restano e escono dalla prova")
    a = ap.parse_args(argv)
    if a.prova_famiglia and a.togli_prova:
        ap.error("--prova-famiglia e --togli-prova insieme non hanno senso")
    if a.operazioni and not a.prova_famiglia:
        ap.error("--operazioni vale solo con --prova-famiglia (l'installazione normale usa operazioni-<dominio>.json)")
    if a.tieni_cambiate and not a.togli_prova:
        ap.error("--tieni-cambiate vale solo con --togli-prova")
    if a.togli_prova:
        return togli_prova(a.dest, a.manifesto, a.prova, a.tieni_cambiate)
    dest = a.dest or DESTINAZIONE
    if a.prova_famiglia:
        return prova_famiglia(a.prova_famiglia, dest, a.manifesto, a.prova, a.operazioni)
    return installa_elenco(dest, a.prova)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
