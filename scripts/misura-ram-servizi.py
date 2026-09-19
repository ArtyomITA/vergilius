r"""Misura la RAM vera di occhi (Holo su CPU), sintesi vocale (pocket-tts) e ponte voce (sherpa-onnx).

Avvia ogni servizio con lo STESSO comando del boot, aspetta che la porta risponda, misura a riposo,
fa una richiesta vera dove si puo' (un'immagine a Holo, una frase al TTS), rimisura, poi spegne.
Non tocca la GPU: Holo gira con CUDA_VISIBLE_DEVICES vuoto e -ngl 0, come in produzione.

Uso: python scripts\misura-ram-servizi.py
"""
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path

W = Path(__file__).resolve().parent.parent
FLAGS = 0x08000000 | 0x00000200  # NO_WINDOW | NEW_PROCESS_GROUP


def porta(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=1):
            return True
    except OSError:
        return False


def attendi(p, s):
    t0 = time.time()
    while time.time() - t0 < s:
        if porta(p):
            return round(time.time() - t0, 1)
        time.sleep(1)
    return None


def ram_albero(pid):
    """(working set MB, privati MB, n processi) del processo e dei suoi figli."""
    ps = (
        "$all = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId;"
        f"$ids = New-Object System.Collections.Generic.List[int]; $ids.Add({pid});"
        "$i = 0; while ($i -lt $ids.Count) { $p = $ids[$i]; "
        "$all | Where-Object { $_.ParentProcessId -eq $p } | ForEach-Object { if (-not $ids.Contains([int]$_.ProcessId)) { $ids.Add([int]$_.ProcessId) } }; $i++ };"
        "$pr = Get-Process -Id $ids -ErrorAction SilentlyContinue;"
        "'{0} {1} {2}' -f [int](($pr | Measure-Object WorkingSet64 -Sum).Sum/1MB), "
        "[int](($pr | Measure-Object PrivateMemorySize64 -Sum).Sum/1MB), @($pr).Count"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    try:
        a, b, c = r.stdout.strip().split()
        return int(a), int(b), int(c)
    except ValueError:
        return 0, 0, 0


def libera():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def png(lato=512):
    """PNG a quadri generato senza librerie: serve solo a far lavorare l'encoder visivo."""
    righe = b""
    for y in range(lato):
        riga = bytearray([0])
        for x in range(lato):
            v = 230 if ((x // 64) + (y // 64)) % 2 else 40
            riga += bytes((v, 255 - v, (x * 255) // lato))
        righe += bytes(riga)

    def pezzo(tipo, dati):
        c = struct.pack(">I", len(dati)) + tipo + dati
        return c + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + pezzo(b"IHDR", struct.pack(">IIBBBBB", lato, lato, 8, 2, 0, 0, 0))
            + pezzo(b"IDAT", zlib.compress(righe, 6)) + pezzo(b"IEND", b""))


def chiudi(proc):
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def misura(nome, cmd, p, attesa, env=None, uso=None):
    if porta(p):
        print(f"{nome}: porta {p} gia' occupata, salto (spegni lo stack prima)")
        return
    prima = libera()
    proc = subprocess.Popen(cmd, cwd=str(W), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=FLAGS)
    try:
        t = attendi(p, attesa)
        if t is None:
            print(f"{nome}: NON partito entro {attesa}s")
            return
        time.sleep(8)
        ws, pv, n = ram_albero(proc.pid)
        print(f"{nome:14} avvio {t:5.1f}s | a riposo: working set {ws:5d} MB, privati {pv:5d} MB ({n} processi) "
              f"| RAM libera {prima} -> {libera()} MB")
        if uso:
            try:
                esito = uso()
            except Exception as e:  # noqa: BLE001
                esito = f"richiesta fallita: {type(e).__name__} {str(e)[:80]}"
            ws2, pv2, _ = ram_albero(proc.pid)
            print(f"{'':14} dopo l'uso ({esito}): working set {ws2:5d} MB, privati {pv2:5d} MB | RAM libera {libera()} MB")
    finally:
        chiudi(proc)
        time.sleep(3)


def usa_holo():
    img = base64.b64encode(png()).decode()
    corpo = json.dumps({"model": "holo", "max_tokens": 60, "temperature": 0, "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Descrivi l'immagine in una frase."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img}}]}]}).encode()
    t0 = time.time()
    req = urllib.request.Request("http://127.0.0.1:8095/v1/chat/completions", data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
    return f"1 immagine 512x512, {d.get('usage', {}).get('prompt_tokens', '?')} token, {time.time() - t0:.0f}s"


def usa_tts():
    """PocketTTS ha un endpoint solo, POST /tts, e vuole multipart/form-data.

    La versione precedente gli mandava JSON su /v1/audio/speech e su /tts: il
    primo non esiste, il secondo rispondeva 422. Risultato, la misura diceva
    "nessun endpoint ha risposto" e la RAM sotto carico non si vedeva mai.
    """
    import uuid
    frase = "Buongiorno, questa e' una prova di sintesi vocale."
    confine = uuid.uuid4().hex
    corpo = b""
    for chiave, valore in (("text", frase), ("voice_url", "giovanni")):
        corpo += (f'--{confine}\r\nContent-Disposition: form-data; '
                  f'name="{chiave}"\r\n\r\n{valore}\r\n').encode()
    corpo += f"--{confine}--\r\n".encode()
    try:
        req = urllib.request.Request("http://127.0.0.1:8014/tts", data=corpo,
                                     headers={"Content-Type": "multipart/form-data; boundary=" + confine})
        t0 = time.time()
        primo = None
        n = 0
        with urllib.request.urlopen(req, timeout=300) as r:
            while True:
                p = r.read1(8192)
                if not p:
                    break
                if primo is None:
                    primo = time.time() - t0
                n += len(p)
        # WAV 16 bit mono a 24 kHz: i byte dicono quanti secondi di voce sono.
        secondi = max(0.0, (n - 44) / 2 / 24000)
        return (f"1 frase su /tts, {n // 1024} KB = {secondi:.1f}s di voce, "
                f"primo byte {primo or 0:.2f}s, totale {time.time() - t0:.1f}s")
    except Exception as e:  # noqa: BLE001
        return f"sintesi non riuscita ({type(e).__name__}): misura solo a riposo"


if __name__ == "__main__":
    print(f"RAM libera all'inizio: {libera()} MB\n")
    voce = W / "tts-venv" / "Scripts"
    server = next((str(W / c / "llama-server.exe") for c in ("llama-cuda124-new", "llama")
                   if (W / c / "llama-server.exe").exists()), "")
    misura("occhi (Holo)", [server, "--host", "127.0.0.1", "--port", "8095",
                            "-m", str(W / "models/vlm/Holo-3.1-0.8B.Q6_K.gguf"),
                            "--mmproj", str(W / "models/vlm/Holo-3.1-0.8B.mmproj-f16.gguf"),
                            "-ngl", "0", "-t", "6", "-c", "8192", "--jinja", "--reasoning", "off",
                            "--chat-template-kwargs", '{"enable_thinking":false}',
                            "--image-min-tokens", "1024", "--image-max-tokens", "2304"],
           8095, 240, env=dict(os.environ, CUDA_VISIBLE_DEVICES=""), uso=usa_holo)
    misura("sintesi (TTS)", [str(voce / "pocket-tts.exe"), "serve", "--language", "italian", "--quantize",
                             "--host", "127.0.0.1", "--port", "8014"], 8014, 180, uso=usa_tts)
    misura("ponte voce", [str(voce / "python.exe"), str(W / "voce" / "ponte_voce.py")], 8013, 180)
    print(f"\nRAM libera alla fine: {libera()} MB")
