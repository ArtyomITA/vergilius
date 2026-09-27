# PROVE: note-calcolatrice-esplora (rinominata da calcolatrice-blocco-note-esplora: "calcolatrice" e' un prefisso vietato in verifica-skill.py, PREFISSI_VIETATI include "calcola")

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| alias italiani: "calcolatrice"->calculator/calcolatrice, "blocco note"->notepad, "esplora file"->explorer | odysseus/src/tool_execution.py:745-752 (`_ALIAS_FINESTRE`) | P13, P14 |
| doppio clic (clicks>=2) e' SEMPRE irreversibile (chiede scheda), anche su un'etichetta altrimenti innocua: Esplora file nasconde le estensioni reali | odysseus/src/tool_execution.py:1327-1334 (`azione_desktop_irreversibile`, ramo Click, commento R4) | nessuna (fatto di codice, motiva P14 quando si apre una sottocartella) |
| la mappa etichetta-coordinate scade dopo ogni azione e dopo un tempo massimo: le coordinate dei pulsanti vanno rilette, non riusate | odysseus/src/tool_execution.py:1112-1119 (`_MAPPA_PC`, `_MAPPA_PC_DURATA_S`) | nessuna (fatto di codice, stessa fonte di guarda-trova-elemento) |
| vista_schermo con `focus` legge pannelli/controlli con le loro coordinate | odysseus/src/vista/schemi.py:11-28 | P13, P14 |

Token: da misurare con verifica-pc.py.
