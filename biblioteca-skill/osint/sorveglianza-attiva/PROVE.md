# PROVE: sorveglianza-attiva

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_sorveglianza: azione (elenca/aggiungi/rimuovi/pulisci/avvisi), bersaglio, luogo, raggio_km, id | odysseus/src/shadowbroker/schemi.py:296-317 | descrizione: watch persistente, non ricerca one-shot |
| elenca default se azione omessa; avvisi legge gli avvisi gia' spinti dal watchdog | odysseus/src/agent_tools/shadowbroker_tools.py:812-822 (`SorveglianzaTool.run`) | |
| aggiungi con luogo crea un'area (geofence), raggio default 100 (clamp 5-3000); senza luogo serve bersaglio | odysseus/src/agent_tools/shadowbroker_tools.py:832-854 | errore esplicito se ne' luogo ne' bersaglio (righe 850-852) |
| rimuovi richiede id (da elenca); errore esplicito se assente | odysseus/src/agent_tools/shadowbroker_tools.py:823-828 | |
| aggiungi/rimuovi/pulisci sono scritture: richiedono OPENCLAW_ACCESS_TIER=full, dichiarato nel messaggio d'errore | odysseus/src/agent_tools/shadowbroker_tools.py:805-810 (docstring), 855-859 | |

Token: da misurare con verifica-skill.py.
