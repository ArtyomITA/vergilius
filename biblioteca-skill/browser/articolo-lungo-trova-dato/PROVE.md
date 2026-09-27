# PROVE: articolo-lungo-trova-dato (mai iniettato; lo legge il revisore)

Ogni affermazione della skill con la sua fonte. Il revisore rilegge ogni riga nel codice; una citazione che non regge = skill respinta.

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| browser_open vuole solo `url` assoluto http/https | odysseus/src/agent_tools/browser_tools.py:175-180 (schema), 772-778 (controllo) | A04, A05, C11 |
| browser_open mostra il testo leggibile sotto "--- page text ---", al massimo 4000 caratteri | browser_tools.py:97 (`_MAX_PAGE_TEXT_IN_TREE`), 852-860 | A04 |
| browser_read {} = testo leggibile dalla TESTA; `refs:true` = albero degli elementi | browser_tools.py:181-190 (schema), 914-950 | A04, A05 |
| browser_read taglia dalla testa a 9000 caratteri con avviso "Page text cut ... Use browser_find" | browser_tools.py:96, 864-876 | A04 |
| il tetto del turno taglia l'esito a 8000 con "…[output troncato a 8000 caratteri]" (l'avviso sopra si perde) | vergilius-lfm.env:61; odysseus/src/agent_loop.py:7581-7590 | A04 |
| browser_find vuole solo `text` (1-500 caratteri) | browser_tools.py:191-196 (schema), 953-963 | A04, A05, C11 |
| browser_find = sottostringa senza maiuscole su OGNI riga dello snapshot aria, 3 righe di contesto, nessun tetto sulle corrispondenze | Playwright MCP 0.0.82: npm-cache/_npx/53b5ca06f5b71ebd/node_modules/playwright-core/lib/coreBundle.js, `packages/playwright-core/src/tools/backend/find.ts` (contextLines = 3) | A04 (trappola "Parigi" a 137k prima di "gemellat" a 152k) |
| righe di stato "blocked: login/captcha", "left_open (rejecting needs a paid subscription)" | odysseus/src/browser_consent.py:74-101, 269-284 | C16, C17, C18 |
| rispondere solo dal testo della pagina | browser_tools.py:102-106 (`LEGGI_COSI`) | tutte |

Token (vocabolario LFM2.5 dal GGUF, resa senza nome): 299 iniettati, descrizione 24.
