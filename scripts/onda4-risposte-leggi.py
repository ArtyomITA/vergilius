r"""Legge i dump *.risposta.json (giri con tool, non-stream) di un braccio: telemetria llama.cpp.

Uso: python scripts/onda4-risposte-leggi.py TAG [TAG2 ...]
Per ogni braccio: richieste, prompt_n processati (dopo cache) e tok/s di prefill, token generati e
tok/s, quota di reasoning (caratteri), finish_reason, chiamate per giro, giri senza chiamata con tool
nominati nel reasoning (Type-1 nel giro), reasoning che dice «rispondo direttamente» e poi chiama (Type-2).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

O = Path("d:/vergilius-lab/ricerche/opt-1080/misure/onda4")
TOOL_RE = re.compile(r"\b(fin_\w+|osint_\w+|web_search|web_fetch)\b")
DIRETTO_RE = re.compile(r"rispond(?:o|ere) direttamente|non (?:serve|servono|ho bisogno di)|answer directly|no tool", re.I)


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0


def braccio(tag):
    fs = sorted((O / f"dump-{tag}").glob("*.risposta.json"))
    if not fs:
        print(f"{tag}: nessun *.risposta.json"); return
    rows = []
    for f in fs:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        m = d.get("message") or {}
        t = d.get("timings") or {}
        u = d.get("usage") or {}
        calls = m.get("tool_calls") or []
        rag = m.get("reasoning_content") or ""
        cont = m.get("content") or ""
        rows.append({
            "file": f.name, "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
            "pred_n": t.get("predicted_n"), "pred_ms": t.get("predicted_ms"),
            "cache_n": t.get("cache_n"), "finish": d.get("finish_reason"),
            "calls": len(calls), "nomi": [c.get("function", {}).get("name") for c in calls],
            "rag_c": len(rag), "cont_c": len(cont),
            "type1": bool(TOOL_RE.search(rag)) and not calls,
            "type2": bool(DIRETTO_RE.search(rag)) and bool(calls),
            "compl": u.get("completion_tokens"),
        })
    print(f"\n=== {tag}: {len(rows)} giri con tool ===")
    pn = [r["prompt_n"] for r in rows if r["prompt_n"] is not None]
    pp = [r["prompt_n"] / r["prompt_ms"] * 1000 for r in rows if r.get("prompt_ms") and r["prompt_n"]]
    big = [r["prompt_n"] / r["prompt_ms"] * 1000 for r in rows if r.get("prompt_ms") and (r["prompt_n"] or 0) > 2000]
    gen = [r["pred_n"] / r["pred_ms"] * 1000 for r in rows if r.get("pred_ms") and r["pred_n"]]
    print(f"prompt_n processati: mediana {med(pn)} max {max(pn) if pn else 0}; >2000: {sum(1 for x in pn if x > 2000)}/{len(pn)}; "
          f"cache_n mediana {med([r['cache_n'] for r in rows if r['cache_n'] is not None])}")
    print(f"prefill tok/s: mediana {med(pp):.0f}; sui prompt >2000: {min(big):.0f}-{max(big):.0f}" if big else f"prefill tok/s mediana {med(pp):.0f}")
    print(f"decode tok/s mediana {med(gen):.1f}; token generati mediana {med([r['pred_n'] for r in rows if r['pred_n']])}")
    print(f"reasoning caratteri mediana {med([r['rag_c'] for r in rows])} max {max(r['rag_c'] for r in rows)}; contenuto mediana {med([r['cont_c'] for r in rows])}")
    print(f"finish_reason {Counter(r['finish'] for r in rows)}; chiamate/giro {Counter(r['calls'] for r in rows)}")
    print(f"Type-1 (tool nel reasoning, nessuna chiamata) {sum(r['type1'] for r in rows)}; Type-2 {sum(r['type2'] for r in rows)}")
    print("tool:", Counter(n for r in rows for n in r["nomi"]).most_common(8))


if __name__ == "__main__":
    for tag in sys.argv[1:] or ["B7"]:
        braccio(tag)
