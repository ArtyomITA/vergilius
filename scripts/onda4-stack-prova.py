"""Stack di prova per l'onda 4: stesso stack di `vergilius-lite`, ma con DB e memoria separati.

  avvia : SB backend 8000 · llama-swap 8012 (config di produzione, stesso binario e flag)
          · ChromaDB 8101 su COPIA di chroma-data · Odysseus 7000 con DATABASE_URL su
          data/app-prova.db, CHROMADB_PORT 8101, ODYSSEUS_LLM_DUMP attivo.
  ferma : uccide tutto (alberi di processo compresi: llama-server figlio di llama-swap).

Produzione: config.yaml intatto; app.db intatto; chroma-data intatto. Log in
ricerche/opt-1080/misure/onda4/stack/. Odysseus resta sulla 7000 apposta: gli harness
(`prova_e2e_agente.py`, gate nero immutabile) puntano li'.
"""
import json, os, shutil, socket, subprocess, sys, time
from pathlib import Path

W = Path("d:/assistenteeee")
OUT = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
STACK = OUT / "stack"
CHROMA_PROVA = OUT / "chroma-prova"
DUMP = OUT / "dump"
PIDS = STACK / "pids.json"
FLAGS = 0x08000000 | 0x00000200


def porta(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=0.3):
            return True
    except OSError:
        return False


def attendi(p, s):
    t0 = time.time()
    while time.time() - t0 < s:
        if porta(p):
            return True
        time.sleep(1)
    return porta(p)


def spawn(nome, cmd, cwd, env=None):
    log = open(STACK / f"{nome}.log", "ab", buffering=0)
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                         env=env or os.environ.copy(), creationflags=FLAGS, close_fds=True)
    print(f"  {nome}: pid {p.pid}", flush=True)
    return p.pid


def avvia():
    STACK.mkdir(parents=True, exist_ok=True); DUMP.mkdir(exist_ok=True)
    for p in (7000, 8000, 8012, 8100, 8101):
        if porta(p):
            print(f"RIFIUTO: porta {p} occupata (stack acceso?)"); sys.exit(1)
    if not CHROMA_PROVA.exists():
        shutil.copytree(W / "chroma-data", CHROMA_PROVA)
        print("  chroma-data copiato in chroma-prova", flush=True)
    if not (W / "odysseus/data/app-prova.db").exists():
        shutil.copy2(W / "odysseus/data/app.db", W / "odysseus/data/app-prova.db")
    pids = {}
    env_sb = os.environ.copy(); env_sb["SHADOWBROKER_STARTUP_HEAVY_REFRESH_DELAY_S"] = "1"
    pids["sb-backend"] = spawn("sb-backend",
        [str(W / "shadowbroker/backend/venv/Scripts/python.exe"), "main.py"],
        W / "shadowbroker/backend", env_sb)
    pids["llama-swap"] = spawn("llama-swap",
        [str(W / "llama-swap/llama-swap.exe"), "--config", os.environ.get("ONDA4_SWAP_CONFIG") or str(W / "llama-swap/config.yaml"),
         "--listen", "127.0.0.1:8012", "--watch-config"], W / "llama-swap")
    pids["chromadb"] = spawn("chromadb",
        [str(W / "chroma-venv/Scripts/chroma.exe"), "run", "--host", "127.0.0.1",
         "--port", "8101", "--path", str(CHROMA_PROVA)], W)
    ok = attendi(8012, 45), attendi(8101, 90), attendi(8000, 120)
    print(f"  pronte 8012/8101/8000: {ok}", flush=True)
    env_o = os.environ.copy()
    env_o.update({
        "DATABASE_URL": "sqlite:///D:/assistenteeee/odysseus/data/app-prova.db",
        "CHROMADB_PORT": "8101",
        "ODYSSEUS_LLM_DUMP": str(DUMP),
        "ODYSSEUS_STARTUP_PROFILE": "vergilius-lite",
        "ODYSSEUS_STARTUP_WARMUPS": "1",
        "ODYSSEUS_AVATAR2D_ENABLED": "0",
    })
    pids["odysseus"] = spawn("odysseus",
        [str(W / "odysseus/venv/Scripts/python.exe"), "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", "7000"], W / "odysseus", env_o)
    PIDS.write_text(json.dumps(pids), encoding="utf-8")
    print(f"  odysseus 7000 pronto: {attendi(7000, 240)}", flush=True)


def ferma():
    if PIDS.exists():
        for nome, pid in json.loads(PIDS.read_text()).items():
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            print(f"  {nome} ({pid}) fermato", flush=True)
        PIDS.unlink()
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false"],
                   capture_output=True)
    time.sleep(2)
    print("  porte:", {p: porta(p) for p in (7000, 8000, 8012, 8101)}, flush=True)


def riavvia_odysseus():
    """Riavvia SOLO Odysseus con variabili extra: `riavvia-odysseus TAG KEY=VAL ...`.
    Log in stack/odysseus-TAG.log, dump in dump-TAG/. Il resto dello stack resta su."""
    tag = sys.argv[2]
    extra = dict(a.split("=", 1) for a in sys.argv[3:])
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}
    if "odysseus" in pids:
        subprocess.run(["taskkill", "/PID", str(pids["odysseus"]), "/T", "/F"], capture_output=True)
    # 19 set 2026: il taskkill per pid non bastava sempre (la vecchia istanza restava sulla 7000, la nuova
    # moriva con Errno 10048 e la suite misurava l'env PRECEDENTE: LH0 falsata). Ora: uccidi chi ascolta
    # sulla 7000, aspetta porta libera, e se non si libera RIFIUTA invece di fingere.
    for _ in range(30):
        if not porta(7000):
            break
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
        for ln in out.splitlines():
            if ":7000 " in ln and "LISTENING" in ln:
                subprocess.run(["taskkill", "/PID", ln.split()[-1], "/T", "/F"], capture_output=True)
        time.sleep(1)
    if porta(7000):
        print("  RIFIUTO: porta 7000 ancora occupata, pronto: False", flush=True)
        sys.exit(1)
    dump = OUT / f"dump-{tag}"; dump.mkdir(exist_ok=True)
    env_o = os.environ.copy()
    env_o.update({
        "DATABASE_URL": "sqlite:///D:/assistenteeee/odysseus/data/app-prova.db",
        "CHROMADB_PORT": "8101",
        "ODYSSEUS_LLM_DUMP": str(dump),
        "ODYSSEUS_STARTUP_PROFILE": "vergilius-lite",
        "ODYSSEUS_STARTUP_WARMUPS": "1",
        "ODYSSEUS_AVATAR2D_ENABLED": "0",
    })
    env_o.update(extra)
    pids["odysseus"] = spawn(f"odysseus-{tag}",
        [str(W / "odysseus/venv/Scripts/python.exe"), "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", "7000"], W / "odysseus", env_o)
    PIDS.write_text(json.dumps(pids), encoding="utf-8")
    pronto = attendi(7000, 240)
    # "pronto" solo se a rispondere e' il processo appena lanciato (vivo), non un fantasma
    vivo = subprocess.run(["tasklist", "/FI", f"PID eq {pids['odysseus']}"], capture_output=True, text=True).stdout
    pronto = pronto and str(pids["odysseus"]) in vivo
    print(f"  odysseus-{tag} 7000 pronto: {pronto}  extra={extra}", flush=True)


if __name__ == "__main__":
    {"avvia": avvia, "ferma": ferma, "riavvia-odysseus": riavvia_odysseus}[sys.argv[1]]()
