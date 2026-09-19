"""Onda 4, blocco precondizioni: O3, O4, OPP, O14, O15 (vedi 35-onda4-piano-rivisto.md §7).

Server isolato porta 5899, stessi flag di produzione (ling: Q6_K, ctx 49152, KV q8_0, FA on,
b 2048 / ub 1024, cache-ram 0) piu' --verbose per vedere le righe TRC dei checkpoint.
Produzione intatta. Rifiuta di partire con llama-server/llama-swap gia' accesi.

  O3   checkpoint su ibrido (#24055): stesso prefisso + append su slot pinnato ->
       prompt_n deve essere ~ il delta, non l'intero prompt. Due percorsi: /completion
       grezzo e /v1/chat/completions con tools (template jinja vero).
  O4   slot pinnato: prefisso caldo su slot 0, freddo su slot 1, poi sfratto e ritorno;
       infine scheduler senza id_slot.
  OPP  prefill del server a 7000 token freddi (tok/s) + probe 4 token (ms/token).
  O14  llama-bench a parita' (KV q8_0, FA, b/ub) con profondita' 0/8192/16384/32768.
       Server SPENTO durante il bench.
  O15  FA Pascal oltre 24K: prompt ~20k poi ~30k + 64 token; server vivo dopo? Ultimo,
       su server fresco: se crasha non rompe gli altri.

Progresso: una riga per passo. JSON scritto dopo ogni passo. --riprendi <json>: salta i
test gia' chiusi, rifa' quello interrotto.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("d:/assistenteeee")
SERVER = ROOT / "llama-cuda124-new/llama-server.exe"
BENCH = ROOT / "llama-cuda124-new/llama-bench.exe"
MODEL = ROOT / "models/Ling-3.0-tiny-Q6_K.gguf"
USCITA = ROOT / "ricerche/opt-1080/misure/onda4"
PORTA = 5899
URL = f"http://127.0.0.1:{PORTA}"

FLAG_SERVER = ["-m", str(MODEL), "--host", "127.0.0.1", "--port", str(PORTA),
               "--ctx-size", "49152", "--reasoning", "on",
               "--temp", "1.0", "--top-p", "0.95", "--top-k", "20",
               "--batch-size", "2048", "--ubatch-size", "1024",
               "--n-gpu-layers", "999", "-fa", "on",
               "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
               "--cache-ram", "0", "--load-mode", "mmap", "--metrics",
               "--slot-save-path", str(USCITA / "slotsave"), "--verbose"]

ap = argparse.ArgumentParser()
ap.add_argument("--riprendi", type=str, default=None)
ap.add_argument("--solo", type=str, default=None, help="O3,O4,OPP,O14,O15")
args = ap.parse_args()

USCITA.mkdir(parents=True, exist_ok=True)
(USCITA / "slotsave").mkdir(exist_ok=True)
if args.riprendi:
    fout = Path(args.riprendi)
    dati = json.loads(fout.read_text(encoding="utf-8"))
else:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fout = USCITA / f"precondizioni-{stamp}.json"
    dati = {"flag_server": FLAG_SERVER, "test": {}}
LOG = fout.with_suffix(".server.log")


def salva():
    fout.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")


def riga(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def processi_llama():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process llama-server,llama-swap,llama-cli,llama-bench -ErrorAction SilentlyContinue | Measure-Object).Count"],
                         capture_output=True, text=True, timeout=30).stdout.strip()
    return int(out or "0")


if processi_llama() > 0:
    print("RIFIUTO: processi llama attivi (server/swap/cli/bench). Spegnere prima.")
    sys.exit(1)

# ---------------- server ----------------
_server = None
_logf = None


def avvia_server():
    global _server, _logf
    _logf = open(LOG, "a", encoding="utf-8", errors="replace")
    _server = subprocess.Popen([str(SERVER)] + FLAG_SERVER, stdout=_logf, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL)
    for _ in range(180):
        time.sleep(2)
        if _server.poll() is not None:
            raise RuntimeError("server morto in avvio")
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=2)
            riga("server pronto")
            return
        except Exception:
            pass
    raise RuntimeError("server non pronto in 360 s")


def ferma_server():
    global _server, _logf
    if _server and _server.poll() is None:
        _server.kill()
        _server.wait(timeout=30)
    if _logf and not _logf.closed:
        _logf.flush(); _logf.close()
    _server = None
    time.sleep(3)


def server_vivo():
    try:
        urllib.request.urlopen(f"{URL}/health", timeout=3)
        return True
    except Exception:
        return False


def log_pos():
    return LOG.stat().st_size if LOG.exists() else 0


def log_da(pos):
    with open(LOG, "rb") as f:
        f.seek(pos)
        testo = f.read().decode("utf-8", errors="replace")
    righe = [r for r in testo.splitlines()
             if "checkpoint" in r or "forcing full" in r or "n_past" in r and "prompt" in r]
    return righe[-12:]


def post(percorso, corpo, timeout=900):
    req = urllib.request.Request(f"{URL}{percorso}", data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    d["_wall_s"] = round(time.time() - t0, 2)
    return d


def n_token(testo):
    return len(post("/tokenize", {"content": testo})["tokens"])


def testo_di(n_tok, seme="A"):
    """Testo vario (niente ripetizione esatta) di circa n_tok token, misurato via /tokenize."""
    base = ("Il {i}° rapporto {s} descrive la manutenzione della centrale idrica di {c}: "
            "portata {p} litri al secondo, pressione {q} bar, temperatura {t} gradi, "
            "interventi programmati per il giorno {g} con squadra {sq}. ")
    citta = ["Trento", "Bari", "Lecco", "Aosta", "Enna", "Pisa", "Udine", "Fermo"]
    parti, i = [], 0
    while True:
        parti.append(base.format(i=i, s=seme, c=citta[i % 8], p=100 + i * 7, q=3 + i % 9,
                                 t=10 + i % 25, g=1 + i % 28, sq=chr(65 + i % 26)))
        i += 1
        if i % 40 == 0:
            t = "".join(parti)
            n = n_token(t)
            if n >= n_tok:
                return t, n


def fatto(nome):
    return dati["test"].get(nome, {}).get("chiuso") is True


def chiudi(nome, esito):
    dati["test"][nome]["chiuso"] = True
    dati["test"][nome]["esito"] = esito
    salva()
    riga(f"=== {nome} CHIUSO: {esito}")


def vuoi(nome):
    if args.solo and nome not in args.solo.split(","):
        return False
    return not fatto(nome)


def compl(prompt, slot, n_predict=8):
    corpo = {"prompt": prompt, "n_predict": n_predict, "temperature": 0, "cache_prompt": True,
             "id_slot": slot}
    p0 = log_pos()
    d = post("/completion", corpo)
    tm = d.get("timings", {})
    return {"prompt_n": tm.get("prompt_n"), "prompt_ms": tm.get("prompt_ms"),
            "cache_n": tm.get("cache_n"), "tokens_cached": d.get("tokens_cached"),
            "id_slot": d.get("id_slot"), "predicted_n": tm.get("predicted_n"),
            "wall_s": d["_wall_s"], "log": log_da(p0)}


T = {"type": "string"}
STRUMENTI = [{"type": "function", "function": {"name": n, "description": f"Strumento {n}.",
              "parameters": {"type": "object", "properties": {"q": T}, "required": ["q"]}}}
             for n in ["manage_memory", "ask_user", "update_plan", "trigger_research",
                       "osint_notizie", "osint_situazione", "osint_dettaglio", "osint_mappa",
                       "osint_web", "fin_mercati", "fin_appalti", "fin_insider", "fin_archivio"]]


def chat(messages, slot, max_tokens=8):
    corpo = {"model": "ling", "messages": messages, "tools": STRUMENTI, "max_tokens": max_tokens,
             "temperature": 0, "cache_prompt": True, "id_slot": slot, "stream": False}
    p0 = log_pos()
    d = post("/v1/chat/completions", corpo)
    tm = d.get("timings", {})
    msg = ((d.get("choices") or [{}])[0].get("message")) or {}
    return {"prompt_n": tm.get("prompt_n"), "prompt_ms": tm.get("prompt_ms"),
            "cache_n": tm.get("cache_n"), "wall_s": d["_wall_s"],
            "content": (msg.get("content") or "")[:80],
            "reasoning": (msg.get("reasoning_content") or "")[:80], "log": log_da(p0)}


try:
    # ================= O3 =================
    if vuoi("O3") or vuoi("O4") or vuoi("OPP"):
        avvia_server()

    if vuoi("O3"):
        r = dati["test"].setdefault("O3", {"passi": {}})
        riga("O3 preparo prefisso ~6000 token")
        P, nP = testo_di(6000, "O3")
        r["prefisso_token"] = nP
        riga(f"O3 prefisso {nP} token")
        a = compl(P, 0);                       r["passi"]["A_freddo"] = a; salva()
        riga(f"O3 A freddo: prompt_n {a['prompt_n']} cache_n {a['cache_n']} {a['wall_s']}s")
        b = compl(P + " Domanda aggiunta: quanto vale la portata a Trento?", 0)
        r["passi"]["B_append"] = b; salva()
        riga(f"O3 B append: prompt_n {b['prompt_n']} cache_n {b['cache_n']} {b['wall_s']}s  log:{len(b['log'])} righe")
        for l in b["log"][-4:]:
            riga("   " + l.strip()[:150])
        P2 = P.replace("Trento", "Torino", 3)   # divergenza a meta' prefisso (simula riscrittura turno vecchio)
        c = compl(P2 + " Domanda aggiunta: quanto vale la portata a Trento?", 0)
        r["passi"]["C_divergente"] = c; salva()
        riga(f"O3 C divergente: prompt_n {c['prompt_n']} cache_n {c['cache_n']} {c['wall_s']}s")
        for l in c["log"][-4:]:
            riga("   " + l.strip()[:150])
        # percorso chat con template jinja + tools
        sys_txt = "Sei Mao, assistente. " + P[:len(P) // 2]
        m1 = [{"role": "system", "content": sys_txt}, {"role": "user", "content": "ciao, come va?"}]
        d1 = chat(m1, 1); r["passi"]["D1_chat_freddo"] = d1; salva()
        riga(f"O3 D1 chat freddo: prompt_n {d1['prompt_n']} cache_n {d1['cache_n']} {d1['wall_s']}s")
        m2 = m1 + [{"role": "assistant", "content": "Bene, grazie. Come posso aiutarti?"},
                   {"role": "user", "content": "quanto sta AAPL adesso?"}]
        d2 = chat(m2, 1); r["passi"]["D2_chat_append"] = d2; salva()
        riga(f"O3 D2 chat append: prompt_n {d2['prompt_n']} cache_n {d2['cache_n']} {d2['wall_s']}s")
        for l in d2["log"][-4:]:
            riga("   " + l.strip()[:150])
        m3 = [m2[0], m2[1], {"role": "assistant", "content": "Bene grazie! Come posso aiutarti oggi?"},
              m2[3], {"role": "assistant", "content": "Controllo."}, {"role": "user", "content": "e MSFT?"}]
        d3 = chat(m3, 1); r["passi"]["D3_chat_turno_vecchio_riscritto"] = d3; salva()
        riga(f"O3 D3 chat riscrittura 2 turni indietro: prompt_n {d3['prompt_n']} cache_n {d3['cache_n']} {d3['wall_s']}s")
        for l in d3["log"][-4:]:
            riga("   " + l.strip()[:150])
        ok_b = (b["prompt_n"] or 10**9) <= 0.15 * nP
        ok_d = (d2["prompt_n"] or 10**9) <= 0.15 * (d1["prompt_n"] or 1)
        chiudi("O3", f"append grezzo {'PASS' if ok_b else 'FAIL'} ({b['prompt_n']}/{nP}); "
                     f"append chat {'PASS' if ok_d else 'FAIL'} ({d2['prompt_n']}/{d1['prompt_n']}); "
                     f"divergenza a meta': {c['prompt_n']}/{nP}; riscrittura 2 indietro: {d3['prompt_n']}")

    # ================= O4 =================
    if vuoi("O4"):
        r = dati["test"].setdefault("O4", {"passi": {}})
        P, nP = testo_di(6000, "O4"); r["prefisso_token"] = nP
        Q, nQ = testo_di(6000, "Q4")
        s0a = compl(P, 0); r["passi"]["1_P_slot0"] = s0a; salva()
        riga(f"O4 1 P su slot0 (freddo): prompt_n {s0a['prompt_n']} {s0a['wall_s']}s")
        s0b = compl(P + " fine.", 0); r["passi"]["2_P_slot0_bis"] = s0b; salva()
        riga(f"O4 2 P+append su slot0: prompt_n {s0b['prompt_n']} cache_n {s0b['cache_n']}")
        s1 = compl(P + " fine.", 1); r["passi"]["3_P_slot1"] = s1; salva()
        riga(f"O4 3 stesso P su slot1: prompt_n {s1['prompt_n']} (atteso freddo se checkpoint slot-locali)")
        sq = compl(Q, 0); r["passi"]["4_Q_slot0_sfratto"] = sq; salva()
        riga(f"O4 4 Q su slot0 (sfratta P): prompt_n {sq['prompt_n']}")
        s0c = compl(P + " fine.", 0); r["passi"]["5_P_slot0_dopo_sfratto"] = s0c; salva()
        riga(f"O4 5 P di nuovo su slot0: prompt_n {s0c['prompt_n']} (atteso freddo con cache-ram 0)")
        corpo = {"prompt": P + " fine.", "n_predict": 8, "temperature": 0, "cache_prompt": True}
        p0 = log_pos(); dsch = post("/completion", corpo)
        sched = {"id_slot": dsch.get("id_slot"), "prompt_n": dsch.get("timings", {}).get("prompt_n"),
                 "log": log_da(p0)}
        r["passi"]["6_P_senza_id_slot"] = sched; salva()
        riga(f"O4 6 P senza id_slot: scheduler ha scelto slot {sched['id_slot']}, prompt_n {sched['prompt_n']} (slot1 ha P caldo)")
        pin_ok = (s0b["prompt_n"] or 10**9) <= 0.15 * nP
        chiudi("O4", f"pin slot0 {'PASS' if pin_ok else 'FAIL'}; slot1 freddo: {s1['prompt_n']}/{nP}; "
                     f"dopo sfratto: {s0c['prompt_n']}/{nP}; scheduler -> slot {sched['id_slot']} prompt_n {sched['prompt_n']}")

    # ================= OPP =================
    if vuoi("OPP"):
        r = dati["test"].setdefault("OPP", {"passi": {}})
        P7, n7 = testo_di(7000, "PP")
        f = compl(P7, 2, n_predict=1); r["passi"]["freddo_7000"] = f; salva()
        tps = (f["prompt_n"] or 0) / (f["prompt_ms"] or 1) * 1000
        riga(f"OPP prefill freddo {f['prompt_n']} token in {f['prompt_ms']:.0f} ms = {tps:.0f} tok/s (bench diceva 1963, server storico 553)")
        r["prefill_tok_s"] = round(tps, 1)
        pr = compl("Ciao, tutto bene?", 3, n_predict=1); r["passi"]["probe_4tok"] = pr; salva()
        mspt = (pr["prompt_ms"] or 0) / max(pr["prompt_n"] or 1, 1)
        riga(f"OPP probe {pr['prompt_n']} token: {pr['prompt_ms']:.0f} ms = {mspt:.1f} ms/token (>50 = sospetto fallback CPU)")
        r["probe_ms_per_token"] = round(mspt, 1)
        chiudi("OPP", f"prefill server {tps:.0f} tok/s a 7000 token freddi; probe {mspt:.1f} ms/token")

    if _server is not None:
        ferma_server()

    # ================= O14 =================
    if vuoi("O14"):
        r = dati["test"].setdefault("O14", {})
        riga("O14 llama-bench a parita' (q8_0/FA/b2048/ub1024), profondita' 0/8192/16384/32768, ~10 min")
        p = subprocess.run([str(BENCH), "-m", str(MODEL), "-p", "512", "-n", "0",
                            "-d", "0,8192,16384,32768", "-ctk", "q8_0", "-ctv", "q8_0",
                            "-fa", "1", "-b", "2048", "-ub", "1024", "-r", "2", "-o", "json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, timeout=3600)
        try:
            res = json.loads(p.stdout)
            curva = {f"pp512@d{x['n_depth']}": round(x["avg_ts"], 1) for x in res}
        except Exception:
            curva = {"errore": p.stdout[-500:] + p.stderr[-500:]}
        r["curva"] = curva; salva()
        riga(f"O14 curva: {curva}")
        # stessa curva SENZA KV q8 (f16) per isolare il costo della quantizzazione KV
        p = subprocess.run([str(BENCH), "-m", str(MODEL), "-p", "512", "-n", "0",
                            "-d", "0,8192", "-fa", "1", "-b", "2048", "-ub", "1024", "-r", "2", "-o", "json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, timeout=1800)
        try:
            res = json.loads(p.stdout)
            curva16 = {f"pp512@d{x['n_depth']}_f16": round(x["avg_ts"], 1) for x in res}
        except Exception:
            curva16 = {"errore": p.stdout[-300:]}
        r["curva_f16"] = curva16; salva()
        riga(f"O14 controllo KV f16: {curva16}")
        chiudi("O14", f"q8_0: {curva}; f16: {curva16}")

    # ================= O15 =================
    if vuoi("O15"):
        r = dati["test"].setdefault("O15", {"passi": {}})
        avvia_server()
        for target in (20000, 30000):
            Pn, nn = testo_di(target, f"FA{target}")
            riga(f"O15 prompt {nn} token + 64 decode, FA on KV q8_0 ...")
            try:
                e = compl(Pn, 0, n_predict=64)
                vivo = server_vivo()
                r["passi"][f"{target}"] = {"token": nn, "prompt_n": e["prompt_n"], "prompt_ms": e["prompt_ms"],
                                          "predicted_n": e["predicted_n"], "wall_s": e["wall_s"], "server_vivo": vivo}
                riga(f"O15 {nn} token: prompt {e['prompt_ms']/1000:.1f}s, generati {e['predicted_n']}, server vivo {vivo}")
            except Exception as ex:
                vivo = server_vivo()
                r["passi"][f"{target}"] = {"token": nn, "errore": f"{type(ex).__name__}: {ex}"[:200], "server_vivo": vivo}
                riga(f"O15 {nn} token: ERRORE {type(ex).__name__}, server vivo {vivo}")
            salva()
            if not vivo:
                break
        ferma_server()
        tutti = all(p.get("server_vivo") and p.get("predicted_n") == 64 for p in r["passi"].values())
        chiudi("O15", "PASS: FA regge 30k su Pascal" if tutti else f"FAIL: {r['passi']}")

finally:
    ferma_server()

riga(f"fine. risultati: {fout}")
