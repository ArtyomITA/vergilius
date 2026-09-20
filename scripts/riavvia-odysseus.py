r"""Riavvia SOLO Odysseus (porta 7000) passando dal Vergilius Boot, cosi' riparte con lo stesso
ambiente di produzione (vergilius.env, vergilius-hardware.env, vergilius-<modello>.env, profilo).
Serve dopo una modifica a un .py di Odysseus o a un file .env. Il boot (:7001) deve essere su.
Uso: python scripts\riavvia-odysseus.py
"""
import json
import socket
import subprocess
import sys
import time
import urllib.request

BOOT = "http://127.0.0.1:7001"


def porta(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=1):
            return True
    except OSError:
        return False


def chi_ascolta(p):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return {r.split()[-1] for r in out.splitlines() if f":{p} " in r and "LISTENING" in r}


def leggi(url, dati=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(dati).encode() if dati is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


stato = leggi(f"{BOOT}/api/status")
profilo = stato.get("profile")
if not profilo:
    print("il boot non ha un profilo scelto: avvia dal boot, non da qui")
    sys.exit(1)
print("profilo:", profilo, flush=True)

for pid in chi_ascolta(7000):
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
for _ in range(20):
    if not porta(7000):
        break
    time.sleep(1)
print("porta 7000 libera:", not porta(7000), flush=True)

# Stesso profilo: il boot riattiva solo cio' che manca (le porte gia' aperte le salta).
leggi(f"{BOOT}/api/profile", {"profile": profilo})
t0 = time.time()
pronto = False
for _ in range(300):
    time.sleep(2)
    try:
        s = leggi(f"{BOOT}/api/status", timeout=5)
    except Exception:  # noqa: BLE001
        continue
    comp = {c["id"]: c["status"] for c in s.get("components", [])}
    if comp.get("odysseus") == "ready" and comp.get("odysseus-warmup") == "ready":
        pronto = True
        break
print(f"odysseus pronto: {pronto} dopo {time.time() - t0:.0f}s", flush=True)
sys.exit(0 if pronto else 1)
