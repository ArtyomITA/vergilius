"""Installa in Odysseus le skill della biblioteca che hanno superato il banco (stanza 3, 27 set 2026).

Uso: odysseus\\venv\\Scripts\\python.exe scripts\\installa-biblioteca.py [--prova]

Regole del piano chiuso (PLAN v4, obiettivo 4):
- sorgenti in biblioteca-skill\\<dominio>\\<nome>\\SKILL.md (versionate), PROVE.md accanto e MAI installato;
- si copia una skill SOLO se il suo nome e' in biblioteca-skill\\INSTALLATE.txt (lo aggiunge il LEAD dopo il
  verdetto TIENI del banco A-B-B-A) E se scripts\\verifica-skill.py le da' zero errori;
- destinazione odysseus\\data\\skills\\<category>\\<name>\\SKILL.md; rieseguirlo ripristina le skill che il modello
  avesse modificato con manage_skills.
--prova: dice cosa farebbe, senza scrivere.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
BIBLIOTECA = RADICE / "biblioteca-skill"
ELENCO = BIBLIOTECA / "INSTALLATE.txt"
DESTINAZIONE = RADICE / "odysseus" / "data" / "skills"
PYTHON = RADICE / "odysseus" / "venv" / "Scripts" / "python.exe"
VERIFICA = RADICE / "scripts" / "verifica-skill.py"
OPERAZIONI_VERIFICA = RADICE / "scripts" / "operazioni-browser.json"


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


def categoria(skill: Path) -> str:
    for riga in skill.read_text(encoding="utf-8").splitlines()[1:40]:
        if riga.startswith("category:"):
            return riga.split(":", 1)[1].strip().strip('"') or skill.parent.parent.name
        if riga.strip() == "---":
            break
    return skill.parent.parent.name


def verifica(skill: Path) -> bool:
    cmd = [str(PYTHON), str(VERIFICA)]
    if OPERAZIONI_VERIFICA.exists():
        cmd += ["--operazioni-verifica", str(OPERAZIONI_VERIFICA)]
    cmd.append(str(skill))
    esito = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if esito.returncode != 0:
        print(esito.stdout[-1500:])
    return esito.returncode == 0


def main(argv: list[str]) -> int:
    prova = "--prova" in argv
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
        if not verifica(skill):
            print(f"[scartata] {nome}: verifica-skill.py ha trovato errori")
            errori += 1
            continue
        dest = DESTINAZIONE / categoria(skill) / nome / "SKILL.md"
        if prova:
            print(f"[prova] {skill} -> {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill, dest)
        print(f"[installata] {nome} -> {dest}")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
