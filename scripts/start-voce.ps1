# Avvia i due servizi della voce locale.
#   8014 = PocketTTS (sintesi)
#   8013 = ponte OpenAI-compatibile che Odysseus interroga
# Entrambi girano su CPU: la GPU resta dedicata a QwenPaw.

$venv = 'd:\assistenteeee\tts-venv\Scripts'

Write-Host "avvio PocketTTS su :8014 ..."
Start-Process -FilePath "$venv\pocket-tts.exe" `
  -ArgumentList 'serve', '--language', 'italian', '--quantize', '--host', '127.0.0.1', '--port', '8014' `
  -RedirectStandardError d:\assistenteeee\voce\pockettts.log `
  -RedirectStandardOutput d:\assistenteeee\voce\pockettts.out.log `
  -WindowStyle Hidden

Write-Host "avvio ponte voce su :8013 ..."
Start-Process -FilePath "$venv\python.exe" `
  -ArgumentList 'd:\assistenteeee\voce\ponte_voce.py' `
  -RedirectStandardError d:\assistenteeee\voce\ponte.log `
  -RedirectStandardOutput d:\assistenteeee\voce\ponte.out.log `
  -WindowStyle Hidden

Write-Host "fatto. Verifica con: curl http://127.0.0.1:8013/health"
