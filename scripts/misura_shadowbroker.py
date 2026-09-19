"""Quanto costa in token una risposta di ShadowBroker.

La domanda decisiva prima di scrivere l'agente: il nostro 9B ha 48K di contesto.
Se una singola risposta ne mangia 30K, l'agente muore alla seconda domanda —
che e' esattamente quello che e' successo a chi ci ha provato con Ollama.

Stima a ~3.6 caratteri per token, come gli altri script di misura del progetto:
buona per confronti relativi, non per numeri assoluti.
"""

import json
import sys
import time
import urllib.request

SB = "http://127.0.0.1:8000"
CONTESTO = 49152          # il nostro profilo base
CONTESTO_VISTA = 32768    # profilo con proiettore


def token(testo: str) -> int:
    return round(len(testo) / 3.6)


def chiama(cmd, args=None, timeout=60):
    corpo = json.dumps({"cmd": cmd, "args": args or {}}).encode()
    req = urllib.request.Request(
        f"{SB}/api/ai/channel/command",
        data=corpo,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            grezzo = r.read().decode()
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"
    return grezzo, time.time() - t0, ""


def riga(etichetta, grezzo, ms, errore, note=""):
    if errore:
        print(f"  {etichetta:<46} ERRORE  {errore[:60]}")
        return 0
    tk = token(grezzo)
    pct = tk / CONTESTO * 100
    bandiera = "  <-- ENORME" if pct > 25 else ("  <- pesante" if pct > 10 else "")
    print(f"  {etichetta:<46} {tk:>7} tok  {pct:>5.1f}%  {ms:>5.1f}s{bandiera} {note}")
    return tk


def main():
    print(f"=== risposte di ShadowBroker, in token (contesto nostro: {CONTESTO}) ===\n")

    print("-- catalogo strumenti (costo fisso di ogni richiesta) --")
    try:
        with urllib.request.urlopen(f"{SB}/api/ai/tools", timeout=30) as r:
            strumenti = r.read().decode()
        d = json.loads(strumenti)
        n = len(d.get("tools") or d.get("commands") or [])
        riga(f"GET /api/ai/tools ({n} strumenti)", strumenti, 0.0, "")
    except Exception as e:
        print(f"  errore: {e}")

    try:
        with urllib.request.urlopen(f"{SB}/api/ai/capabilities", timeout=30) as r:
            cap = r.read().decode()
        riga("GET /api/ai/capabilities", cap, 0.0, "")
    except Exception as e:
        print(f"  errore: {e}")

    print("\n-- letture leggere (quelle che l'agente dovrebbe usare) --")
    for etichetta, cmd, args in [
        ("channel_status", "channel_status", {}),
        ("get_summary compact", "get_summary", {"compact": True}),
        ("get_summary NON compact", "get_summary", {}),
        ("what_changed", "what_changed", {"compact": True}),
        ("search_news 'conflict' limit=5", "search_news", {"query": "conflict", "compact": True, "limit": 5}),
        ("search_news 'conflict' SENZA limite", "search_news", {"query": "conflict"}),
        ("find_flights 'AF1'", "find_flights", {"query": "AF1", "compact": True}),
        ("entities_near Kyiv r=50km", "entities_near", {"lat": 50.45, "lng": 30.52, "radius_km": 50, "compact": True}),
        ("brief_area Kyiv r=100km", "brief_area", {"lat": 50.45, "lng": 30.52, "radius_km": 100, "compact": True}),
        ("get_correlations", "get_correlations", {"compact": True}),
    ]:
        grezzo, ms, err = chiama(cmd, args)
        riga(etichetta, grezzo or "", ms, err)

    print("\n-- fette di layer (il percorso principale secondo loro) --")
    for etichetta, layers, extra in [
        ("get_layer_slice [gdelt]", ["gdelt"], {}),
        ("get_layer_slice [gdelt] limit 10", ["gdelt"], {"limit_per_layer": 10}),
        ("get_layer_slice [news]", ["news"], {}),
        ("get_layer_slice [military_flights]", ["military_flights"], {}),
        ("get_layer_slice [military_flights] lim 10", ["military_flights"], {"limit_per_layer": 10}),
        ("get_layer_slice conflitti (4 layer)", ["gdelt", "liveuamap", "frontlines", "telegram_osint"], {}),
        ("get_layer_slice conflitti lim 10", ["gdelt", "liveuamap", "frontlines", "telegram_osint"], {"limit_per_layer": 10}),
    ]:
        args = {"layers": layers, "compact": True}
        args.update(extra)
        grezzo, ms, err = chiama(etichetta and "get_layer_slice", args)
        riga(etichetta, grezzo or "", ms, err)

    print("\n-- scarichi completi (da NON usare, misurati per sapere il prezzo) --")
    for etichetta, cmd, args in [
        ("search_telemetry 'conflict'", "search_telemetry",
         {"query": "conflict", "compact": True, "confirm_expensive": True}),
        ("get_slow_telemetry", "get_slow_telemetry", {"confirm_expensive": True}),
        ("get_telemetry", "get_telemetry", {"confirm_expensive": True}),
    ]:
        grezzo, ms, err = chiama(cmd, args, timeout=180)
        riga(etichetta, grezzo or "", ms, err)


if __name__ == "__main__":
    main()
