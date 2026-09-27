# PROVE: mappa-mostra

| affermazione | fonte (file:riga) | note |
|---|---|---|
| osint_mappa: azione (required, enum centra/livelli/evidenzia/preset/ripristina/nota/note/cancella_nota), preset, luogo, lat, lng, zoom, accendi, ids, testo, colore, id | odysseus/src/shadowbroker/schemi.py:197-243 | la skill usa solo centra/evidenzia/livelli/preset/ripristina: nota/note/cancella_nota fuori scope (annotazioni, non richieste dal DOSSIER) |
| zoom: 1 world, 6 country, 10 city (descrizione schema) | odysseus/src/shadowbroker/schemi.py:230 | la skill aggiunge 5 per un mare, coerente con area-cosa-vola |
| centra accetta anche un nome noto o un id come "luogo"; se non risolve, chiama il geocoder e spiega come uscirne | odysseus/src/agent_tools/shadowbroker_tools.py:463-497 (`MappaTool.run`, ramo centra; `_aiuto_centra`) | corregge il difetto Mar Nero: prima centra falliva secco senza dire come procedere |
| ids per evidenzia: "mai ticker azionari o nomi di aziende" | odysseus/src/shadowbroker/schemi.py:233-235 | |
| livelli E preset spengono entrambi il resto (entrambi chiamano set_layers con "solo":True) | odysseus/src/agent_tools/shadowbroker_tools.py:530-533 (livelli, "solo": bool(accesi) and not spenti, di fatto True quando accendi e' passato senza spegni), 542-551 (preset, "solo": True esplicito) | CORREZIONE: la bozza pipeline-osint-finanza.md e la mia prima versione dicevano che preset NON spegne il resto, citando schemi.py:207-209 (che descrive il chip Financial via routes/shadowbroker_routes.py, un percorso diverso) e uno spezzone di commento (righe 566-579) che sta dentro il ramo evidenzia, non preset. Errore reale trovato da FINANZA (chat #23), verificato di persona: preset del TOOL osint_mappa e' esclusivo come livelli |
| osint_mappa e' registrato UI_SIDE_EFFECT (armano il varco: evidenzia, livelli, preset, ripristina); SOLO le azioni centra/focus/vola scendono a sola vista (UI_VIEW_ONLY, nessuna approvazione), per nome esatto dello strumento | odysseus/src/tool_capabilities.py:291-300 (registrazione), 486-505 (`_VIEW_ONLY_ACTIONS`, decisione del 26 set) | verificato di persona in questa sessione, non ereditato dalla bozza |
| osint_geocode: azione (required), luogo; risultato in "risultati" | odysseus/src/shadowbroker/schemi.py:344-362; odysseus/src/agent_tools/shadowbroker_tools.py:922-944 | stessa nota di area-cosa-vola sulla chiave italiana |

Token: da misurare con verifica-skill.py.
