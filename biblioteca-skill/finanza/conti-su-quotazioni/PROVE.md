# PROVE: conti-su-quotazioni (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| `calcola` vuole `espressioni` (lista, obbligatoria), fino a 20 per chiamata | odysseus/src/agent_tools/calc_tools.py:153 (`voci = [...][:20]`), 217-259 (schema, `required: ["espressioni"]`) | in attesa operazioni-finanza.json |
| un modello piccolo sbaglia l'aritmetica multi-cifra: mai calcolare a mente | calc_tools.py:1-9 (commento del modulo: "un modello da 2-3B sbaglia l'aritmetica a piu' cifre (misurato: 3 x 309,48 = 284,39)") | |
| ogni voce torna col proprio risultato o col proprio errore; un errore non blocca le altre | calc_tools.py:159-176 (`fuori = []`, try/except per voce, `ZeroDivisionError`, `ValueError`/`SyntaxError`/`TypeError`/`OverflowError`) | |
| fin_mercati {"titolo":"<name>"} solo se serve un prezzo live, non se il numero e' gia' in chat | schemi.py:481-499; scelta di flusso, non un vincolo del codice | |
| funzioni ammesse: numeri, `+ - * / % ** ( )`, `round`, `abs`, `min`, `max`, `sum`, `sqrt`, `media`, `percento`, `variazione_percento`; niente nomi di variabile | calc_tools.py:27-47 (`_OP_BIN`, `_OP_UN`, `_FUNZIONI`), 111-121 (`_valuta`: solo Constant/BinOp/UnaryOp/Name in `_COSTANTI`/Call in `_FUNZIONI`, altrimenti "elemento non ammesso") | |
| `variazione_percento` prende PRIMA il valore vecchio | calc_tools.py:45 (`"variazione_percento": lambda prima, dopo: (dopo - prima) / prima * 100`) | |
| una conversione senza cambio dato dall'utente: chiedere, mai inventare il tasso | nessun tasso di cambio live nel codice (nessun tool fin_* o osint_* lo fornisce, confermato su schemi.py); dedotto | |
| i risultati sono esatti, arrotondare solo in scrittura | calc_tools.py:177 (`"nota": "risultati esatti: riportali cosi', arrotonda solo in scrittura"`) | |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 296 iniettati, descrizione 22.
