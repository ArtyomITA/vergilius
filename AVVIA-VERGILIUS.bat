@echo off
rem Doppio click: parte SOLO Vergilius Boot (porta 7001), la pagina dei profili.
rem Finche' non scegli un profilo, non parte nient'altro. Il .ps1 diretto viene
rem bloccato dalla execution policy di Windows, questo wrapper la scavalca.
rem Il boot apre da solo il browser su http://127.0.0.1:7001 (--open).
powershell -NoProfile -ExecutionPolicy Bypass -File "d:\assistenteeee\scripts\avvia-tutto.ps1"
echo.
echo Scegli il profilo nella pagina del browser (http://127.0.0.1:7001).
pause
