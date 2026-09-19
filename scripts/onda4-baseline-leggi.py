"""Legge il baseline E2E dell'onda 4 e stampa i numeri che contano.

Fonti (tutte prodotte dallo stack di prova, `onda4-stack-prova.py`):
  - stack/odysseus.log   righe `[agent-timing]`: round_start (prompt_tokens), first_event,
                         round_stream_done (text_chars, tool_calls) per round.
  - stack/llama-swap.log righe di llama-server `prompt eval time = X ms / N tokens` e
                         `eval time`: prompt_n davvero processati (dopo cache) e tok/s.
  - dump/*.json          payload inviati: hash del prefisso (system + tools) per richiesta,
                         per vedere quanto spesso cambia tra round e tra turni (E06/E09).

Uso: python scripts/onda4-baseline-leggi.py [cartella misure/onda4]
"""
import hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

O = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
# uso: leggi.py [TAG]  -> stack/odysseus-TAG.log e dump-TAG/ ; senza TAG = braccio A
TAG = sys.argv[1] if len(sys.argv) > 1 else ""
LOGF = O / ("stack/odysseus-%s.log" % TAG if TAG else "stack/odysseus.log")
DUMPD = O / ("dump-%s" % TAG if TAG else "dump")

# ---------- agent-timing ----------
righe = LOGF.read_text(encoding="utf-8", errors="replace").splitlines()
turni, cur = [], None
for r in righe:
    m = re.search(r"\[agent-timing\] round_start round=(\d+) .*?prompt_tokens=(\d+)", r)
    if m:
        rnd = int(m.group(1))
        if rnd == 1:
            cur = {"ts": r[:19], "round": []}
            turni.append(cur)
        if cur is not None:
            cur["round"].append({"n": rnd, "prompt_tokens": int(m.group(2))})
        continue
    m = re.search(r"\[agent-timing\] first_event round=(\d+) elapsed=([\d.]+)s", r)
    if m and cur and cur["round"]:
        cur["round"][-1]["ttft"] = float(m.group(2))
        continue
    m = re.search(r"\[agent-timing\] round_stream_done round=(\d+) elapsed=([\d.]+)s text_chars=(\d+) tool_calls=(\d+)", r)
    if m and cur and cur["round"]:
        cur["round"][-1].update({"elapsed": float(m.group(2)), "chars": int(m.group(3)),
                                 "calls": int(m.group(4))})

print(f"turni agentici nel log: {len(turni)}")
# contatori delle leve onda 4 (righe di log, una per evento)
_cont = {k: sum(1 for r in righe if k in r) for k in
         ("[tool-freeze]", "[tool-dedup] hit", "[fresh-required]", "[slot-erase] slot", "nessuna route",
          "[model-gate] cancelling background", "timeout", "Traceback")}
print("eventi: " + "  ".join(f"{k}={v}" for k, v in _cont.items()) + "\n")
print(f"{'turno':6} {'ora':9} {'round':>5} {'tok round1':>10} {'TTFT r1':>8} {'somma round s':>13} {'tool calls':>10}")
tot = []
for i, t in enumerate(turni, 1):
    rr = t["round"]
    somma = sum(x.get("elapsed", 0) for x in rr)
    calls = sum(x.get("calls", 0) for x in rr)
    tot.append(somma)
    print(f"{i:6} {t['ts'][11:19]:9} {len(rr):5} {rr[0]['prompt_tokens']:10} "
          f"{rr[0].get('ttft', 0):8.1f} {somma:13.1f} {calls:10}")
if tot:
    s = sorted(tot)
    print(f"\nsomma round per turno: mediana {s[len(s)//2]:.1f}s  p95 {s[int(len(s)*0.95)-1 if len(s)>1 else 0]:.1f}s  max {s[-1]:.1f}s")

# prompt_tokens per round (quanto e' grande il prompt a ogni giro: cresce = append)
print("\nprompt_tokens per round (primi 6 turni):")
for i, t in enumerate(turni[:6], 1):
    print(f"  turno {i}: " + " -> ".join(str(x['prompt_tokens']) for x in t["round"]))

# ---------- llama-server timings ----------
sw = (O / "stack/llama-swap.log")
if sw.exists():
    txt = sw.read_text(encoding="utf-8", errors="replace")
    # offset segnato da onda4-braccio.py: solo le righe di QUESTO braccio
    offf = O / ("stack/llama-swap.offset-%s" % TAG) if TAG else None
    if offf and offf.exists():
        raw = sw.read_bytes()[int(offf.read_text().strip() or 0):]
        txt = raw.decode("utf-8", errors="replace")
        print(f"\nllama-swap: dall'offset {offf.read_text().strip()} ({len(txt)} caratteri di questo braccio)")
    pe = [(int(n), float(ms)) for ms, n in re.findall(r"prompt eval time =\s+([\d.]+) ms /\s+(\d+) tokens", txt)]
    if pe:
        print(f"\nllama-server, {len(pe)} richieste: prompt_n processati (dopo cache)")
        ns = sorted(n for n, _ in pe)
        print(f"  mediana {ns[len(ns)//2]}  p90 {ns[int(len(ns)*0.9)-1]}  max {ns[-1]}  "
              f"richieste >2000 token: {sum(1 for n in ns if n > 2000)}/{len(ns)}")
        grandi = [(n, ms) for n, ms in pe if n > 2000]
        if grandi:
            tps = [n / ms * 1000 for n, ms in grandi]
            print(f"  prefill grandi: {min(tps):.0f}-{max(tps):.0f} tok/s")

# ---------- dump: stabilita' del prefisso ----------
dump = sorted(f for f in DUMPD.glob("*.json") if not f.name.endswith(".risposta.json"))
if dump:
    hs, per_req = [], []
    for f in dump:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = d.get("messages") or []
        sysm = next((m.get("content") for m in msgs if m.get("role") == "system"), "")
        tools = d.get("tools") or []
        nomi = [t.get("function", {}).get("name") for t in tools]
        h = hashlib.sha256((json.dumps(sysm, ensure_ascii=False) + json.dumps(tools, sort_keys=False)).encode()).hexdigest()[:10]
        hs.append(h)
        per_req.append((f.name, h, len(msgs), len(tools), nomi))
    distinti = len(set(hs))
    print(f"\ndump: {len(per_req)} richieste, prefissi (system+tools) distinti: {distinti}")
    cambi = sum(1 for a, b in zip(hs, hs[1:]) if a != b)
    print(f"  cambi di prefisso tra richieste consecutive: {cambi}/{max(len(hs)-1,1)}")
    seq = defaultdict(int)
    for _, h, _, nt, _ in per_req:
        seq[(h, nt)] += 1
    print("  primi 8 payload: file | hash | msg | tools")
    for f, h, nm, nt, nomi in per_req[:8]:
        print(f"    {f} | {h} | {nm:3} | {nt:2} | {', '.join(n for n in nomi[:5] if n)}…")
