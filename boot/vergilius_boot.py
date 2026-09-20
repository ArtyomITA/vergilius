r"""Vergilius Boot — l'ingresso unico dello stack (porta 7001).

Prima di questo server non parte NIENTE: ne' ShadowBroker, ne' llama-swap, ne'
Odysseus. L'utente sceglie il profilo nella pagina (stessa skin di Odysseus),
il loader mostra percentuale e stato di ogni componente, a fine carico si va
alla destinazione (ShadowBroker :3000 o Vergilius :7000).

Profili:
  shadowbroker    dashboard, mappa, radio/SIGINT, feed OSINT. Niente modello.
  vergilius-chat  llama-swap + ChromaDB + Odysseus. NIENTE ShadowBroker.
  vergilius-lite  chat + ShadowBroker (niente voce, niente Avatar 2D).
  full            tutto: lite + PocketTTS + ponte voce + Avatar 2D.

Stdlib pura (http.server): parte in meno di un secondo, nessun venv. Lancia
solo comandi fissi di proprieta' del repo; non accetta path o argomenti dal
browser. La logica dei componenti e' quella di
shadowbroker/backend/services/startup_profiles.py, portata qui perche' il
profilo "chat" non ha ShadowBroker a fare da regia.

Uso: python boot\vergilius_boot.py [--open]
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

PORTA = 7001
WORKSPACE = Path(__file__).resolve().parents[1]


def _leggi_env(nome: str) -> dict:
    """Legge un file `NOME=valore` accanto al progetto (righe vuote e # ignorate).

    Due file, separati apposta:
      vergilius.env           impostazioni valide su qualsiasi macchina
      vergilius-hardware.env  impostazioni tarate su QUESTA GPU/questo server
    Chi clona il progetto puo' cancellare il secondo senza rompere nulla.
    """
    fuori: dict = {}
    f = WORKSPACE / nome
    if not f.exists():
        return fuori
    for riga in f.read_text(encoding="utf-8", errors="replace").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        k, _, v = riga.partition("=")
        k = k.strip()
        if k:
            fuori[k] = v.strip()
    return fuori


def _impostazioni_odysseus() -> dict:
    """Impostazioni per Odysseus: prima quelle universali, poi quelle hardware.
    Una variabile gia' presente nell'ambiente di sistema vince su entrambi i file."""
    valori = _leggi_env("vergilius.env")
    valori.update(_leggi_env("vergilius-hardware.env"))
    # Profilo per modello: `VERGILIUS_MODELLO=lfm` in vergilius.env carica vergilius-lfm.env, che
    # sovrascrive le leve tarate su Ling. Assente o vuoto = nessun profilo (comportamento storico).
    modello = (os.environ.get("VERGILIUS_MODELLO") or valori.get("VERGILIUS_MODELLO") or "").strip().lower()
    if modello:
        valori.update(_leggi_env(f"vergilius-{modello}.env"))
    return {k: v for k, v in valori.items() if k not in os.environ}
LOG_DIR = WORKSPACE / "logs"
PAGINA = Path(__file__).resolve().parent / "boot.html"

P_SB, P_CHAT, P_LITE, P_FULL = "shadowbroker", "vergilius-chat", "vergilius-lite", "full"
PROFILI = {P_SB, P_CHAT, P_LITE, P_FULL}
CON_SB = {P_SB, P_LITE, P_FULL}
CON_ODY = {P_CHAT, P_LITE, P_FULL}

_LOCK = threading.RLock()
_BOOT_ID = uuid.uuid4().hex
_PROFILO: str | None = None
_SCELTO_A: float | None = None
_THREAD: threading.Thread | None = None
_ERRORI: dict[str, str] = {}
_FASE: str = ""   # etichetta del passo in corso, per il loader


def _porta_aperta(porta: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.2):
            return True
    except OSError:
        return False


def _attendi_porta(porta: int, timeout: float) -> bool:
    fine = time.monotonic() + timeout
    while time.monotonic() < fine:
        if _porta_aperta(porta):
            return True
        time.sleep(0.25)
    return _porta_aperta(porta)


def _spawn(nome: str, comando: list[str], *, cwd: Path, porta: int, env: dict | None = None) -> None:
    global _FASE
    if _porta_aperta(porta):
        return
    _FASE = nome
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / f"startup-{nome}.log", "ab")
    flags = 0x08000000 | 0x00000200 if os.name == "nt" else 0  # NO_WINDOW | NEW_PROCESS_GROUP
    try:
        subprocess.Popen(comando, cwd=str(cwd), env=env or os.environ.copy(),
                         stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    except Exception as e:  # pragma: no cover
        _ERRORI[nome] = f"{type(e).__name__}: {e}"


def _attiva(profilo: str) -> None:
    global _FASE
    if profilo in CON_SB:
        sb = WORKSPACE / "shadowbroker"
        env_sb = os.environ.copy()
        env_sb["SHADOWBROKER_STARTUP_HEAVY_REFRESH_DELAY_S"] = "1"
        _spawn("sb-backend", [str(sb / "backend" / "venv" / "Scripts" / "python.exe"), "main.py"],
               cwd=sb / "backend", porta=8000, env=env_sb)
        env_fe = os.environ.copy()
        env_fe["SHADOWBROKER_FRAME_ANCESTORS"] = "'self' http://localhost:7000 http://127.0.0.1:7000"
        fe = sb / "frontend"
        # build production solo se i sorgenti sono piu' recenti di .next/BUILD_ID
        build_id = fe / ".next" / "BUILD_ID"
        # Dashboard gia' in ascolto (boot riavviato a stack acceso): non si ricompila
        # sotto i piedi di un `next start` vivo, e comunque non ci sarebbe nulla da avviare.
        gia_su = _porta_aperta(3000)
        scaduta = not gia_su and not build_id.exists()
        if not scaduta and not gia_su:
            t_build = build_id.stat().st_mtime
            fonti = [fe / "package.json", fe / "package-lock.json", fe / "next.config.ts"]
            for p in (fe / "src").rglob("*"):
                if p.is_file():
                    fonti.append(p)
            scaduta = any(p.exists() and p.stat().st_mtime > t_build for p in fonti)
        if scaduta:
            _FASE = "sb-build"
            try:
                subprocess.run(["npm.cmd", "run", "build"], cwd=str(fe), check=True, timeout=900,
                               creationflags=0x08000000 if os.name == "nt" else 0,
                               stdout=open(LOG_DIR / "startup-sb-build.log", "ab"), stderr=subprocess.STDOUT)
            except Exception as e:
                _ERRORI["sb-frontend"] = f"build fallita: {e}"
        _spawn("sb-frontend", ["npm.cmd", "run", "start"], cwd=fe, porta=3000, env=env_fe)

    if profilo in CON_ODY:
        ls = WORKSPACE / "llama-swap"
        _spawn("llama-swap", [str(ls / "llama-swap.exe"), "--config", str(ls / "config.yaml"),
                              "--listen", "127.0.0.1:8012", "--watch-config"], cwd=ls, porta=8012)
        _spawn("chromadb", [str(WORKSPACE / "chroma-venv" / "Scripts" / "chroma.exe"), "run",
                            "--host", "127.0.0.1", "--port", "8100", "--path", str(WORKSPACE / "chroma-data")],
               cwd=WORKSPACE, porta=8100)
        _attendi_porta(8012, 45)
        _attendi_porta(8100, 90)
        if profilo == P_FULL:
            voce = WORKSPACE / "tts-venv" / "Scripts"
            # PocketTTS chiede a HuggingFace i pesi con clonazione voce (repo
            # riservato: il permesso non ce l'abbiamo), si prende un errore e
            # solo allora ripiega su quelli in cache. Quel giro di rete e' il
            # grosso dell'attesa all'avvio: misurato 12,9 s online contro 7,8 s
            # offline, e molto peggio quando la rete e' lenta.
            # Condizione: pesi italiani e incastro della voce gia' in
            # ~/.cache/huggingface (ci sono; una voce nuova va scaricata una
            # volta con questa riga tolta).
            env_tts = os.environ.copy()
            env_tts["HF_HUB_OFFLINE"] = "1"
            # Non pocket-tts.exe ma il nostro lanciatore: il pacchetto fissa
            # torch a un filo solo e su otto core la sintesi va a un quarto di
            # quello che potrebbe. Misurato sulla stessa frase italiana a caldo:
            # 1 filo fattore tempo reale 0,58 - 2 fili 0,44 - 3 e 4 fili niente
            # di meglio. Stessi argomenti di prima, nessuna modifica a
            # site-packages. Vedi voce/avvia_tts.py.
            _spawn("pockettts", [str(voce / "python.exe"), str(WORKSPACE / "voce" / "avvia_tts.py"),
                                 "--language", "italian",
                                 "--quantize", "--host", "127.0.0.1", "--port", "8014"],
                   cwd=WORKSPACE, porta=8014, env=env_tts)
            _spawn("voice-bridge", [str(voce / "python.exe"), str(WORKSPACE / "voce" / "ponte_voce.py")],
                   cwd=WORKSPACE, porta=8013)
        ody = WORKSPACE / "odysseus"
        env_o = os.environ.copy()
        _impost = _impostazioni_odysseus()
        env_o.update(_impost)
        if _impost:
            try:
                (LOG_DIR / "startup-impostazioni.log").write_text(
                    "".join(f"{k}={v}\n" for k, v in sorted(_impost.items())), encoding="utf-8")
            except Exception:
                pass
        env_o["ODYSSEUS_STARTUP_PROFILE"] = profilo
        env_o["ODYSSEUS_AVATAR2D_ENABLED"] = "1" if profilo == P_FULL else "0"
        env_o["ODYSSEUS_STARTUP_WARMUPS"] = "1"
        _spawn("odysseus", [str(ody / "venv" / "Scripts" / "python.exe"), "-m", "uvicorn",
                            "app:app", "--host", "127.0.0.1", "--port", "7000"], cwd=ody, porta=7000, env=env_o)
    _FASE = ""


_PORTE_SB = (8000, 3000)
_PORTE_VOCE = (8013, 8014)
_PORTE_ODY = (7000,)


def _kill_porta(porta: int) -> None:
    """Termina il processo (e il suo albero) in ascolto su una porta locale."""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10,
                             creationflags=0x08000000 if os.name == "nt" else 0).stdout
        pids = {ln.split()[-1] for ln in out.splitlines() if f":{porta} " in ln and "LISTENING" in ln}
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, timeout=15,
                           creationflags=0x08000000 if os.name == "nt" else 0)
    except Exception as e:  # pragma: no cover
        _ERRORI[f"stop-{porta}"] = str(e)


def _cambia(da: str | None, a: str) -> None:
    """Cambio profilo a caldo: spegne cio' che il nuovo profilo non usa, riavvia
    Odysseus (il profilo vive nel suo env) e avvia cio' che manca."""
    global _FASE
    _FASE = "cambio-profilo"
    if a not in CON_SB:
        for p in _PORTE_SB: _kill_porta(p)
        _kill_porta(8787)  # wormhole di SB
    if a != P_FULL:
        for p in _PORTE_VOCE: _kill_porta(p)
    if a in CON_ODY:
        for p in _PORTE_ODY: _kill_porta(p)   # riparte con il nuovo ODYSSEUS_STARTUP_PROFILE
    else:
        for p in _PORTE_ODY: _kill_porta(p)
        _kill_porta(8012); _kill_porta(8100); _kill_porta(8095)
    time.sleep(1.5)
    _attiva(a)


def scegli(profilo: str, cambia: bool = False) -> dict:
    global _PROFILO, _SCELTO_A, _THREAD
    p = str(profilo or "").strip().lower()
    if p not in PROFILI:
        raise ValueError(f"profilo sconosciuto: {p}")
    with _LOCK:
        if _PROFILO and _PROFILO != p and not cambia:
            raise RuntimeError(f"profilo gia' scelto per questo avvio: {_PROFILO}")
        precedente = _PROFILO
        if _PROFILO != p:
            _PROFILO, _SCELTO_A = p, time.time()
            _ERRORI.clear()
            if precedente and cambia:
                _THREAD = threading.Thread(target=_cambia, args=(precedente, p), name=f"boot-cambio-{p}", daemon=True)
                _THREAD.start()
                return stato()
        if _THREAD is None or not _THREAD.is_alive():
            _THREAD = threading.Thread(target=_attiva, args=(p,), name=f"boot-{p}", daemon=True)
            _THREAD.start()
    return stato()


def _json_url(url: str, timeout: float = 0.6):
    try:
        with urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


_FEED_CACHE: dict = {"t": 0.0, "v": {}}


def _feed_sb(*chiavi: str) -> bool:
    """Freschezza feed da /api/startup/feeds (memoria-only, mai il boot: un
    endpoint di SB che richiama il boot creava un ciclo). Cache 1s: lo stato
    ne chiede 5 per chiamata."""
    now = time.monotonic()
    if now - _FEED_CACHE["t"] > 1.0:
        d = _json_url("http://127.0.0.1:8000/api/startup/feeds", 1.5)
        _FEED_CACHE["v"] = (d or {}).get("fresh") or {}
        _FEED_CACHE["t"] = now
    fresh = _FEED_CACHE["v"]
    return any(bool(fresh.get(k)) for k in chiavi)


def _odysseus_pronto() -> bool:
    if not _porta_aperta(7000):
        return False
    d = _json_url("http://127.0.0.1:7000/api/startup-profile-status", 0.4)
    return bool(d and d.get("ready"))


# Feed che vivono di servizi altrui (rete esterna): se sono lenti NON devono
# tenere in ostaggio il "pronto", l'assistente e' gia' utilizzabile. Restano
# visibili come in caricamento e si completano da soli.
_FEED_ESTERNI = {"fast-intelligence", "news-intelligence", "tinygs", "telegram-osint", "wastewater"}
_ATTESA_FEED_S = 90.0


def _c(cid: str, label: str, pronto: bool, detail: str = "") -> dict:
    # Un errore registrato vale finche' il componente non e' su: se intanto la porta risponde
    # (es. build fallita per una gara con un'altra ricompilazione, poi dashboard ripartita)
    # l'errore vecchio non deve tenere in ostaggio il "pronto" per sempre.
    err = "" if pronto else _ERRORI.get(cid, "")
    return {"id": cid, "label": label, "status": "error" if err else ("ready" if pronto else "loading"),
            "detail": err or detail}



# ---------------------------------------------------------------------------
# RAM: svuota il working set dei llama-server che stanno tutti in VRAM.
# Misurato 23 ago 2026: con --load-mode mmap la mappa del GGUF (5,6 GB) resta nel
# working set di llama-server anche se i pesi vivono in VRAM e non vengono piu'
# letti. Windows non la ritira da solo finche' non va in sofferenza (e allora
# paginano Chrome/VS Code, non lei). Un SetProcessWorkingSetSize(-1,-1) la
# sposta in standby: RAM disponibile da 1,5 a 6,4 GB, velocita' invariata
# (tg 33 -> 40 tok/s, pp uguale). Si applica SOLO ai processi con
# --n-gpu-layers 999 (Ling, QwenPaw...): Holo gira su CPU e i suoi pesi li usa.
# ---------------------------------------------------------------------------
_TRIM_OGNI_S = 30
_TRIM_SOGLIA_MB = 1500


def _pid_llama_gpu() -> list[int]:
    """PID dei llama-server.exe con tutti i layer in GPU (riga di comando)."""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='llama-server.exe'", "get", "processid,commandline", "/format:csv"],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout
    except Exception:
        return []
    pids = []
    for riga in out.splitlines():
        if "llama-server" not in riga or "--n-gpu-layers 999" not in riga and "-ngl 999" not in riga:
            continue
        try:
            pids.append(int(riga.strip().split(",")[-1]))
        except ValueError:
            pass
    return pids


def _ws_mb(pid: int) -> float:
    import ctypes, ctypes.wintypes as w
    class PMC(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t)] + [(f"x{i}", ctypes.c_size_t) for i in range(6)]
    h = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0400, False, pid)
    if not h:
        return 0.0
    try:
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / 2 ** 20
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def _trim_ws(pid: int) -> bool:
    import ctypes
    h = ctypes.windll.kernel32.OpenProcess(0x0100 | 0x0400, False, pid)
    if not h:
        return False
    try:
        return bool(ctypes.windll.kernel32.SetProcessWorkingSetSize(h, ctypes.c_size_t(-1), ctypes.c_size_t(-1)))
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def _ciclo_trim() -> None:
    while True:
        time.sleep(_TRIM_OGNI_S)
        try:
            for pid in _pid_llama_gpu():
                if _ws_mb(pid) > _TRIM_SOGLIA_MB:
                    _trim_ws(pid)
        except Exception:
            pass


def avvia_trim_ram() -> None:
    if os.name == "nt":
        threading.Thread(target=_ciclo_trim, name="boot-trim-ram", daemon=True).start()

def stato() -> dict:
    with _LOCK:
        p, a, errori, fase = _PROFILO, _SCELTO_A, dict(_ERRORI), _FASE
    comp: list[dict] = []
    if p in CON_SB:
        comp += [
            _c("sb-backend", "ShadowBroker backend", _porta_aperta(8000)),
            _c("sb-frontend", "Interfaccia e mappa", _porta_aperta(3000),
               "build production in corso…" if fase == "sb-build" else ""),
            _c("fast-intelligence", "Voli, navi e SIGINT", _feed_sb("commercial_flights", "military_flights", "ships", "sigint")),
            _c("news-intelligence", "Notizie e intelligence", _feed_sb("news")),
            _c("tinygs", "TinyGS e satelliti radio", _feed_sb("tinygs_satellites")),
            _c("telegram-osint", "Telegram OSINT", _feed_sb("telegram_osint")),
            _c("wastewater", "Biosorveglianza wastewater", _feed_sb("wastewater")),
        ]
    if p in CON_ODY:
        comp += [
            _c("llama-swap", "Router modelli", _porta_aperta(8012)),
            _c("chromadb", "Memoria vettoriale e RAG", _porta_aperta(8100)),
            _c("odysseus", "Shell Vergilius", _porta_aperta(7000)),
            _c("odysseus-warmup", "RAG, memoria, modelli e strumenti MCP", _odysseus_pronto()),
        ]
    if p == P_FULL:
        comp += [
            _c("pockettts", "Sintesi vocale", _porta_aperta(8014)),
            _c("voice-bridge", "Voce e trascrizione live", _porta_aperta(8013)),
            _c("avatar2d", "Avatar 2D", _porta_aperta(7000)),
        ]
    # Dopo _ATTESA_FEED_S dalla scelta i feed esterni ancora in caricamento
    # smettono di bloccare: "blocking" false li marca per la pagina, che mostra
    # la riga di spiegazione al posto dell'attesa muta.
    trascorso = (time.time() - a) if a else 0.0
    for c in comp:
        c["blocking"] = not (c["id"] in _FEED_ESTERNI and trascorso > _ATTESA_FEED_S)
    # Nel conteggio un feed diventato non bloccante vale come fatto, altrimenti
    # la percentuale resterebbe a meta' con la pagina che dice "tutto pronto".
    fatti = [c["status"] == "ready" or not c["blocking"] for c in comp]
    n_ok = sum(fatti)
    tot = len(comp)
    pronto = bool(p) and tot > 0 and all(fatti) and not any(c["status"] == "error" for c in comp)
    return {
        "ok": True, "boot_id": _BOOT_ID, "profile": p, "selected_at": a,
        "phase": "choose" if not p else ("ready" if pronto else "loading"),
        "progress": round(n_ok / tot * 100) if tot else 0, "ready": pronto, "components": comp,
        "target_url": "http://127.0.0.1:3000" if p == P_SB else "http://127.0.0.1:7000",
    }


# ---------------------------------------------------------------------------
# Istantanea dello stato. Misurato 20 set 2026: `stato()` di solito risponde in
# 40 ms, ma ogni tanto una delle sue sonde si pianta per 7-8 s. Chi interroga
# (pagina del boot, gate di ShadowBroker con timeout corto) leggeva quel buco come
# "nessun profilo scelto" e riproponeva la scelta. Ora lo stato lo calcola un filo
# a parte e la rotta risponde SEMPRE subito con l'ultima istantanea.
# ---------------------------------------------------------------------------
_ISTANTANEA: dict | None = None
_STATO_OGNI_S = 1.0


def _registra_lentezza(durata: float) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "boot-stato-lento.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} stato() ha impiegato {durata:.1f}s\n")
    except Exception:
        pass


def _ciclo_stato() -> None:
    global _ISTANTANEA
    while True:
        t0 = time.monotonic()
        try:
            _ISTANTANEA = stato()
        except Exception:
            pass
        durata = time.monotonic() - t0
        if durata > 1.0:
            _registra_lentezza(durata)
        time.sleep(_STATO_OGNI_S)


def stato_rapido() -> dict:
    """Ultima istantanea con il profilo SEMPRE aggiornato (e' una lettura in memoria)."""
    s = _ISTANTANEA
    with _LOCK:
        p = _PROFILO
    if s is None or s.get("profile") != p:
        return stato()
    return s


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silenzio
        pass

    def _json(self, codice: int, corpo: dict) -> None:
        b = json.dumps(corpo).encode()
        self.send_response(codice)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            return self._json(200, stato_rapido())
        if self.path in ("/", "/index.html"):
            b = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)
            return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/profile"):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                corpo = json.loads(self.rfile.read(n) or b"{}")
                return self._json(200, scegli(corpo.get("profile", ""), cambia=bool(corpo.get("change"))))
            except ValueError as e:
                return self._json(422, {"detail": str(e)})
            except RuntimeError as e:
                return self._json(409, {"detail": str(e)})
        self.send_response(404); self.end_headers()


def main() -> int:
    avvia_trim_ram()
    threading.Thread(target=_ciclo_stato, name="boot-stato", daemon=True).start()
    if "--profilo" in sys.argv:
        scegli(sys.argv[sys.argv.index("--profilo") + 1])
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    if "--open" in sys.argv:
        threading.Timer(0.4, lambda: webbrowser.open(f"http://127.0.0.1:{PORTA}/")).start()
    print(f"Vergilius Boot su http://127.0.0.1:{PORTA}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
