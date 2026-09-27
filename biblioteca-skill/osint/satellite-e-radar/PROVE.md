# PROVE: satellite-e-radar

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_satellite: azione (termico/passaggi, required), luogo, lat, lng, raggio_km, ore | odysseus/src/shadowbroker/schemi.py:416-436 | termico default raggio 10 (max 100); passaggi default ore 24 |
| termico clamp raggio 1-100 default 10; passaggi clamp ore 1-72 default 24; nessun punto -> errore esplicito | odysseus/src/agent_tools/shadowbroker_tools.py:1015-1041 (`SatelliteTool.run`) | "serve un luogo (nome o 'lat,lng')" riga 1025 |
| osint_sar: azione (required, enum stato/anomalie/scene/copertura/aree/aggiungi_area/rimuovi_area/sorveglia/centra), area, luogo, lat, lng, raggio_km, quante | odysseus/src/shadowbroker/schemi.py:441-467 | |
| anomalie con luogo cerca vicino al punto (raggio default 50, clamp 1-2000); senza luogo cerca le piu' recenti ovunque | odysseus/src/agent_tools/shadowbroker_tools.py:1073-1084 (`SarTool.run`) | |
| aggiungi_area, rimuovi_area, sorveglia, centra sono SCRITTURE (tier full) | odysseus/src/agent_tools/shadowbroker_tools.py:1044-1054 (docstring `SarTool`), 1102-1128 (ramo scritture) | esplicito nel commento della classe |
| osint_sar azione="centra" NON eredita la deroga di osint_mappa centra: resta una scrittura per nome esatto dello strumento | odysseus/src/tool_capabilities.py:486-497 (commento: "osint_sar ha una sua azione 'centra' che resta una scrittura") | verificato di persona; corregge un rischio di confusione fra i due "centra" non presente nella bozza originale |
| feed spento (MESH_SAR_OPENCLAW_ENABLED) dichiarato dal backend nel messaggio stesso | odysseus/src/agent_tools/shadowbroker_tools.py:1044-1050 (docstring `SarTool`) | il messaggio d'errore arriva tale e quale all'utente |

Token: da misurare con verifica-skill.py.
