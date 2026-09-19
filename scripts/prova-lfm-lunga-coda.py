"""Coda della catena lunga: aspetta la fine della catena in corsa e la rilancia una volta (completa L1,
saltata perche' la prova a secco aveva scritto il marcatore di fine). Staccata dalla sessione."""
import subprocess, sys, time
from pathlib import Path
STATO = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4/prova-lfm-lunga.txt")
n0 = STATO.read_text(encoding="utf-8", errors="replace").count("CATENA LUNGA FINITA")
while STATO.read_text(encoding="utf-8", errors="replace").count("CATENA LUNGA FINITA") == n0:
    time.sleep(30)
time.sleep(10)
subprocess.run([sys.executable, r"d:\assistenteeee\scripts\prova-lfm-lunga.py"], cwd=r"d:\assistenteeee")
with open(STATO, "a", encoding="utf-8") as f:
    f.write(time.strftime("%H:%M:%S") + " TUTTI I BRACCI FINITI\n")
