r"""Riavvia SOLO il backend di ShadowBroker (porta 8000), lasciando su il resto dello stack.
Stesso comando e stesso ambiente del boot. Serve dopo una modifica a un .py del backend.
Uso: python scripts\riavvia-sb-backend.py
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
BE = W / "shadowbroker" / "backend"
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


for pid in chi_ascolta(8000):
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
for _ in range(20):
    if not porta(8000):
        break
    time.sleep(1)
print("porta 8000 libera:", not porta(8000), flush=True)
if porta(8000):
    sys.exit(1)

LOG.mkdir(exist_ok=True)
env = os.environ.copy()
env["SHADOWBROKER_STARTUP_HEAVY_REFRESH_DELAY_S"] = "1"
subprocess.Popen([str(BE / "venv" / "Scripts" / "python.exe"), "main.py"], cwd=str(BE), env=env,
                 stdout=open(LOG / "startup-sb-backend.log", "ab"), stderr=subprocess.STDOUT,
                 creationflags=NO_WINDOW | 0x00000200)
t0 = time.time()
for _ in range(180):
    if porta(8000):
        break
    time.sleep(1)
print(f"porta 8000 in ascolto: {porta(8000)} dopo {time.time() - t0:.0f}s", flush=True)
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/startup/status", timeout=30) as resp:
        print("stato:", resp.status, resp.read(300).decode("utf-8", "replace"), flush=True)
except Exception as e:  # noqa: BLE001
    print("stato:", type(e).__name__, str(e)[:120], flush=True)
