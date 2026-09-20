r"""Ricompila e riavvia SOLO il frontend di ShadowBroker (porta 3000), lasciando su il resto dello stack.
Stessi comandi e stesso ambiente del boot. Uso: python scripts\riavvia-dashboard.py
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

W = Path(__file__).resolve().parent.parent
FE = W / "shadowbroker" / "frontend"
LOG = W / "logs"
NO_WINDOW = 0x08000000


def porta(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=1):
            return True
    except OSError:
        return False


def chi_ascolta(p):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return {r.split()[-1] for r in out.splitlines() if f":{p} " in r and "LISTENING" in r}


for pid in chi_ascolta(3000):
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
for _ in range(20):
    if not porta(3000):
        break
    time.sleep(1)
print("porta 3000 libera:", not porta(3000), flush=True)

LOG.mkdir(exist_ok=True)
t0 = time.time()
with open(LOG / "startup-sb-build.log", "ab") as f:
    r = subprocess.run(["npm.cmd", "run", "build"], cwd=str(FE), stdout=f, stderr=subprocess.STDOUT,
                       timeout=1200, creationflags=NO_WINDOW)
print(f"build: codice {r.returncode} in {time.time() - t0:.0f}s", flush=True)
if r.returncode != 0:
    sys.exit(1)

env = os.environ.copy()
env["SHADOWBROKER_FRAME_ANCESTORS"] = "'self' http://localhost:7000 http://127.0.0.1:7000"
subprocess.Popen(["npm.cmd", "run", "start"], cwd=str(FE), env=env,
                 stdout=open(LOG / "startup-sb-frontend.log", "ab"), stderr=subprocess.STDOUT,
                 creationflags=NO_WINDOW | 0x00000200)
for _ in range(60):
    if porta(3000):
        break
    time.sleep(1)
import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:3000/", timeout=30) as resp:
        print("dashboard: HTTP", resp.status, flush=True)
except Exception as e:  # noqa: BLE001
    print("dashboard:", type(e).__name__, str(e)[:120], flush=True)
