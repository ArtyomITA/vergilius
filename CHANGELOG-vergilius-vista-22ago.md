# Changelog — Vista, gli occhi di Vergilius (22 ago 2026)

Parte 2 del lavoro VLM: Ling (cervello testuale, GPU) ottiene occhi tramite
**Holo-3.1-0.8B** full-CPU. Parte 1 (test di Holo da solo, debolezze, ottimizzazioni)
in `ricerche/vlm-occhi/07-parte1-*.md`. Ricerca completa in `ricerche/vlm-occhi/`.

## Cosa fa ora l'utente
- Menu `+` in chat → **Vista**. Al click parte loader (Holo si avvia e scalda,
  ~20s la prima volta, 0s se già su). Toggle persistente (localStorage).
- Con Vista accesa, nello stesso turno: **immagini allegate** descritte da Holo,
  **video allegati** descritti frame per frame (ffmpeg 0.5 fps), **modalità
  computer** (Ling guarda con `vista_schermo`/`vista_trova`, agisce con Windows-MCP
  `Snapshot`/`Click`/`Type`/`App`/`Shortcut`, verifica riguardando), **modalità
  browser** (Playwright MCP isolato `builtin_browser`, già presente: `browser_navigate`/
  `browser_snapshot`/`browser_click`/`browser_type`).
- Vista e Intelligence/Financial si sommano (tool set = unione).

## Verifica (doppia, come da skill `aggiungi-tool-modello`)
- **Banco diretto** `odysseus/scripts/prova_modello_vista.py`: 16 casi, catena a 2-3
  giri con risultati finti realistici → **16/16** (da 11/16 single-shot: loop
  "guarda-poi-agisci" è sequenza giusta, non errore).
- **E2E** `scripts/prova_e2e_vista.py` (login, `/api/vista/avvia`, sessione, 4 turni
  `vista_mode=true` sullo schermo REALE) → **4/4 TUTTO OK**. Holo ha visto Chrome
  dell'utente, `vista_schermo` passato dal convertitore nativo (TOOL_TAGS ok),
  "guarda di nuovo" ha riguardato davvero.
- Registro verificato: `vista_*` in TOOL_TAGS, TOOL_HANDLERS, FUNCTION_TOOL_SCHEMAS,
  VISTA_TOOL_NAMES — tutti e 4 i livelli.

## File nuovi
| File | Cosa |
|---|---|
| `odysseus/src/vista/__init__.py` | Docstring con misure che guidano il design |
| `odysseus/src/vista/client.py` | `VistaClient`: avvio on-demand llama-server Holo (porta 8095, `CUDA_VISIBLE_DEVICES=""`, `--reasoning off`, `--chat-template-kwargs enable_thinking=false` AL LANCIO, `--image-min-tokens 1024`), warm-up, `screenshot()` (PIL.ImageGrab), `trova()` (grounding prompt ufficiale H Company + **zoom 2-step automatico** su target piccoli), `descrivi_schermo()`/`descrivi_immagine()` (JSON a schema via `response_format`), `domanda()` (UNA domanda), `descrivi_video()` (ffmpeg → un frame per chiamata). Flag `attiva` = modalità. Singleton `get_vista()`. |
| `odysseus/src/vista/schemi.py` | `VISTA_TOOL_SCHEMAS` (4 tool, description = QUANDO, inglese, esempi IT, <110 tok) + `REGOLE_VISTA` (ricette in positivo: due mondi desktop/browser, loop guarda-agisci-verifica, `App` per aprire programmi, una domanda per chiamata, lingua in testa e coda) |
| `odysseus/src/agent_tools/vista_tools.py` | Handler `SchermoTool`, `TrovaTool`, `ImmagineTool`, `VideoTool` (estendono `_Base`), `_allegato_recente()` dall'indice upload, `VISTA_TOOL_HANDLERS`, `VISTA_TOOL_NAMES`. Nota "Riferisci in italiano" nell'output (non nel prompt: KV intatta) |
| `odysseus/routes/vista_routes.py` | `GET /api/vista/stato`, `POST /api/vista/avvia` (bloccante finché pronto e caldo), `POST /api/vista/ferma` |
| `odysseus/static/js/vista.js` | Toggle + loader (velo non bloccante con spinner), `window.OdysseusVista`, riallineamento all'avvio se era accesa |
| `odysseus/scripts/prova_modello_vista.py` | Banco diretto 16 casi multi-giro |
| `scripts/prova_e2e_vista.py` | E2E attraverso API vera |

## File modificati
| File | Modifica |
|---|---|
| `odysseus/src/agent_tools/__init__.py` | Import protetto `VISTA_TOOL_HANDLERS` → `TOOL_HANDLERS.update`; prefisso `vista_` nella derivazione `TOOL_TAGS` |
| `odysseus/src/tool_schemas.py` | `FUNCTION_TOOL_SCHEMAS.extend(VISTA_TOOL_SCHEMAS)` |
| `odysseus/routes/chat_routes.py` | Flag `vista_mode` (form/body) → `get_vista().attiva`; escalation chat→agent; `REGOLE_VISTA` appese al system (dopo OSINT); `forced_tools` = vista ∪ tool Windows-MCP (da `get_mcp_manager().get_all_tools()`, nomi qualificati vivi) ∪ `mcp__builtin_browser__*` ∪ ALWAYS_AVAILABLE, tolti da `_disabled_finale` |
| `odysseus/src/document_processor.py` | `analyze_image_with_vl_result`: se `get_vista().attiva` → Holo descrive (JSON → 5 righe testo), altrimenti catena vision configurata |
| `odysseus/src/chat_handler.py` | Ramo `elif is_video_file` dopo immagini: Holo descrive i frame (cache `.vision/{id}.txt`), testo `[Video: nome] — frame descritti in ordine, racconta tu la sequenza` |
| `odysseus/src/upload_handler.py` | `is_video_file()` (mp4/mov/mkv/m4v/avi; `.webm` resta audio salvo mime `video/*`) |
| `odysseus/app.py` | `include_router(setup_vista_routes())` |
| `odysseus/static/index.html` | Bottone `#overflow-vista-btn` nel menu `+`; `<script defer src="/static/js/vista.js">` |
| `odysseus/static/js/chat.js` | `fd.append('vista_mode','true')` se `OdysseusVista.attiva()` |
| `architecture-map/components.yaml` | Componente `ody.vista` + archi da chat_routes/tool_schemas/document_processor/chat_handler |

## Secondo giro (22 ago, pomeriggio): boot unico, ling-vista, Windows-MCP studiato a fondo

### Avvio
- **`boot/vergilius_boot.py` (:7001) + `boot/boot.html`**: ingresso unico, stessa skin di
  Odysseus (griglia, Fira Code, viola, scintille). Finché non scegli, **zero processi**.
  4 profili: ShadowBroker, **Vergilius Chat (nuovo: senza ShadowBroker)**, Lite, Full.
  Loader reale (dial con %, stato per componente) — quelli di `StartupGate` spostati qui.
  `avvia-tutto.ps1` riscritto: lancia solo il boot. Testato: `vergilius-chat` 0→100%, SB
  mai partito.
- Backend SB (`startup_profiles.py`) e `StartupGate.tsx` **delegano al boot**: `:3000`
  aperto senza profilo rimanda a `:7001`; scelta da `:3000` viene inoltrata.
- Odysseus legge profilo (`/api/startup-profile-status`): `static/js/profilo.js`
  nasconde Intelligence/Financial in Chat, Voce in Chat/Lite; lato server
  `chat_routes.py` ignora `osint_mode` nel profilo chat.

### Vista dai modelli, non dal toggle
- llama-swap: **`ling-vista`** (stesso Ling; Odysseus lo riconosce e avvia Holo nel
  warmup, `model_routes.py`); **thinking ON** su `ling` e `ling-vista` (banchi 18/18 e
  16/16 confermati); `ling-thinking` rimosso. `llamaswap.status()` espone
  `vista_esterna`/`occhi_pronti`; `modelLoading.js` aspetta anche gli occhi e mostra
  badge **"vista"** (non "senza vista").
- Menu `+`: "Vista" → **Computer** e **Browser** (toggle separati, visibili solo con
  `*-vista`), `vista.js` riscritto. `chat_routes.py`: `computer_mode`/`browser_mode`
  scelgono quali tool MCP forzare.
- Widget Strumenti: CSS sui token del tema, staccato dal bordo (20px), respiro 18px.

### Windows-MCP — studiato (README + codice + skill del repo), due bug trovati
1. **Bug upstream Odysseus (`src/mcp_manager.py`)**: leggeva `tool.inputSchema`; con
   `mcp` 2.0.0 attributo è `input_schema` → `hasattr` False → **schema `{}` per ogni
   tool di ogni server MCP, da sempre**. Modello chiamava `App({})` → Windows-MCP
   `TypeError NoneType` (fuzzy su `name=None`). Fix: helper `_tool_input_schema()`
   compatibile con entrambe le versioni, 3 punti. Verificato: `App` 7 parametri, `Type`
   `required=['text']`.
2. Server MCP rinominato nel DB `075fe6c2` → **`windows`** (backup `app.db.bak-22ago`):
   tool diventano `mcp__windows__App` — leggibili per il 9B.
- Fatti dal codice che le regole ora rispecchiano: **Snapshot NON ha id/label** (solo
  `(x,y)` centro elemento → `Click(loc=[x,y])`); `App(name)` obbligatorio di fatto, nome
  del menu Start (localizzato!); `WaitFor` in timeout solleva; `Scrape` con
  `use_sampling=true` chiede sampling MCP (non supportato) → `false`.
- **Teams (Electron)**: albero UIA fallisce a raffica (`COMError -2146233083`) se la
  finestra non ha già il focus; con il focus regge. Per chat/media apps la regola manda
  agli occhi dopo `App(mode='switch')`.

### Occhi: descrizione neutra, mai domande chiuse (misurato)
- Holo con domande chiuse **inventa per compiacere** ("è Teams? sì" su VS Code; "messaggi
  non letti? sì in alto a destra" inesistenti). JSON neutro legge testo vero
  (ha trascritto i messaggi di questa chat e "3 o più membri fuori sede" di Teams).
- `descrivi_schermo(focus)`: JSON più ricco (`contenuto_principale`, `testo_leggibile`
  ≤12, `contatori_e_badge`) + `focus` = argomento, non domanda. Parametro `domanda`
  rimosso dal tool.
- **`vista_schermo` ritorna SEMPRE entrambe le viste** (scelta utente): `albero_ui`
  (Snapshot compattato a 120 righe, taglio dichiarato) + descrizione occhi, in
  parallelo. Regola del **loop di raffinamento**: se non basta, seconda chiamata con
  focus più stretto.
- E2E reale "aprimi Teams e dimmi se ho nuovi messaggi": `App → App(switch) → Wait →
  Snapshot` → risposta corretta con nomi e date reali dal Teams dell'utente.
- Banco diretto con regole finali (~840 tok): 15/16 in due run (una volta 1 errore,
  una volta 1 senza tool, mai lo stesso caso) = fluttuazione a temp 0.2, non regressione.
  Regole più lunghe costano ~430 token in più sul prefix KV.

### Thinking e "lentezza"
- Misurato: Ling genera a **38 tok/s**; gli "8 tok/s" in UI = testo visibile / tempo
  totale, perché thinking consuma token prima della risposta (200/200 in pensiero su
  "spiegami un mutuo"). Streaming c'è (pensiero nel pannello), risposta appare dopo.
  Opzione non ancora applicata: `--reasoning-budget N` per cappare il pensiero.
- "Custom" come mittente = **preset dell'utente** ("assistente di Adrian chiamata Mao",
  `character_name: Custom`, con istruzioni avatar-emotions): non toccato, da rinominare o
  disattivare da `+ → Prompt`. Si somma alle regole Vista a ogni turno.

## Fix collaterale: browser MCP era morto
`odysseus/src/builtin_mcp.py`: `@playwright/mcp@latest` (senza pin di versione,
upstream) ha rimosso il flag `--output-mode`; server builtin_browser moriva in
avvio con `error: unknown option '--output-mode'` → **nessun tool browser per il
modello**, in silenzio. Tolto il flag (verificato con `--help` della versione
scaricata: `--headless --isolated --snapshot-mode --image-responses` ancora
validi). Dopo il fix: "MCP server connected: Built-in: Browser — 24 tools".
Rischio residuo: `@latest` senza pin può rompersi di nuovo a ogni aggiornamento
upstream del pacchetto.

Preesistente e NON toccato: builtin Python (RAG, Email, Memory, Image Gen)
loggano "Connection closed" all'avvio — presente anche nel log del 21 ago,
prima di ogni modifica di oggi.

## Scoperte durante il lavoro
- **Odysseus teneva in cache la lista modelli vecchia** dell'endpoint llama-swap
  (`ModelEndpoint.cached_models`): `ling` non era selezionabile dalla chat nonostante
  fosse il default. Aggiornata con `GET /api/model-endpoints/6dbaedf8/models?refresh=true`
  (tasto "aggiorna" dell'UI). Da ricordare a ogni modello nuovo in config.yaml.
- Primo turno dopo un tool-result inglese esce in inglese: mitigato con nota
  italiana nell'output del tool.
- Ling risponde dal contesto senza riguardare se domanda è coperta dal turno
  precedente ("Che app è in primo piano?" → "Browser." in 5s senza tool). Accettato:
  per forzare screenshot a ogni turno si paga 4-5s; "guarda di nuovo" funziona.

## Limiti noti / da fare
- Upload chat cap 10MB (`ODYSSEUS_CHAT_UPLOAD_MAX_BYTES`): stretto per video, da alzare via env.
- Holo resta vivo dopo "ferma"? No: `/api/vista/ferma` lo killa. Nessun TTL automatico
  (RAM ~1.1GB residente finché acceso).
- Test E2E con allegati (immagine/video) e con click reali non fatti: il banco non
  deve cliccare sul desktop dell'utente. Da provare a mano dall'UI.
- `.webm` video (non audio) passa solo se browser manda mime `video/webm`.
- Screenshot = schermo primario (PIL.ImageGrab); multi-monitor non gestito.

## 23 ago 2026 — alias llama-swap (fix lentezza)

- `llama-swap/config.yaml`: tolto profilo duplicato `ling-vista`; ora e' `aliases: ["ling-vista"]`
  sotto `ling` + `includeAliasesInList: true` globale. Prima ogni alternanza ling <-> ling-vista
  (chat su -vista, titolo/memorie/skill di Odysseus su `utility_model=ling`) ricaricava il modello
  da disco: 55 s - 2 min 34 s a turno (log), percepito come "2 tok/s". Dopo: un solo processo,
  zero swap, generazione reale 29-35 tok/s. Backup: `config.yaml.bak-23ago-prealias`.
- Diagnosi completa e piano (browser, prompt, wastewater): `ricerche/diagnosi-lentezza-e-browser-ling-23ago.md`
  + `ricerche/velocita-ling-moe-pascal-ricerca-web.md` + `ricerche/browser-agent-modelli-piccoli-e-nanobrowser.md`.

## 23 ago 2026 (pomeriggio) — verifica dei fix di Codex + completamenti

Codex (sessione separata) aveva applicato 10 fix senza poter avviare processi: niente test reali.
Fatto qui:
- **Benchmark runtime misurati** (llama-bench, Ling Q5_K_M, GTX 1080): ubatch 1024 vs 512 =
  pp2048 1963 vs 1629 tok/s (+20 %), pp4096 1618 vs 1474 (+10 %), tg invariata (42-44).
  ubatch 2048: "failed to create context" (VRAM). KV q8_0 vs f16 a ub 1024: pp 1938 vs 712 tok/s,
  tg 43,6 vs 41,8 → resta q8_0 (ipotesi "f16 piu' veloce su Pascal" smentita).
  `--no-mmap --mlock` NON testabile con 2 GB di RAM liberi (servono 5,3 GB): con mmap
  caricamento via llama-swap sceso a 5,6 s (ieri 52 s – 2,5 min).
- **Contesto 131072** (massimo del modello) sul profilo `ling`: misurato 6,5 GB VRAM dopo
  prompt da 18k (49k usava 6,0 GB), 40 tok/s; a 46k di prompt pp 241 tok/s, tg 28. 64k/80k/96k
  provati: 6,1 / 6,2 / 6,3 GB. Tentativo con 3 llama-server residui aveva dato 8 GB pieni e
  hang: probe ora usa PID espliciti.
- **Consenso cookie** (`odysseus/src/builtin_mcp.py`): `--storage-state` con `SOCS=CAI` su
  .youtube.com/.google.com/.google.it + `--init-script` generico (clicca UNA volta "Rifiuta
  tutto"/"Reject all" o "Accetta tutto"/"Accept all", MutationObserver 15 s). File generati in
  `data/local/browser-consent-*`. `ODYSSEUS_BROWSER_CONSENT=0` per spegnerlo. 2 test nuovi.
- **REGOLE_VISTA_LITE** (`odysseus/src/vista/schemi.py`): versione caveman-lite, 846 → ~506 token,
  stesse firme; attiva con `VERGILIUS_REGOLE_VISTA=lite`. Banco `prova_modello_vista.py`
  aggiornato ai nomi nuovi (adapter `browser_*`, `mcp__windows__*`) e con argomento variante.
- **Harness comportamentale Ling** (`scripts/prova_ling_behavior.py`): guardia temperatura
  84 → 90 con pausa di raffreddamento sopra 84 (la 1080 throttla a 83: abortire era inutile).
  Eseguito `--suite all --repeats 2` (526 richieste): risultati in `ricerche/ling-behavior-all-*`.
- **ARC**: evidenze degli edge ops spostate da `scripts/avvia-tutto.ps1` (ora lancia solo il
  boot) a `boot/vergilius_boot.py`; nuovi path/test (browser_tooling_constants, harness Ling,
  test recovery/disclosure); purposes di registry, agent.tools, rt.llm.swap. Doctor 0 errori.
- **Trim RAM** (`boot/vergilius_boot.py`): thread ogni 30 s che svuota working set dei
  llama-server tutti-in-GPU; RAM disponibile 1,5 → 6,4 GB, velocita' invariata. Stesso trim
  nell'harness prima dell'abort RAM.
- **REGOLE_VISTA_LITE default** (banco 15/16 = piena); `VERGILIUS_REGOLE_VISTA=piena` per la lunga.
- **Descrizioni browser_find/click/type** riscritte (harness: find 13 → 70 %, type 25 → 50 %).
- **Harness**: attese per lingua (`args_en`), `scripts/rivaluta_ling_behavior.py` per ri-giudicare.
- **E2E kit browser** 3/4 (example.com, Wikipedia Roma 2.743.357, ricerca YouTube con canali;
  homepage YouTube vuota senza login). Report: `ricerche/verifica-fix-codex-e-test-ling-23ago.md`.

## 23 ago 2026 (sera) — ricerca ottimizzazione GTX 1080

- 20 indagini parallele + fatti misurati sulla macchina: `ricerche/opt-1080/` (17.600 righe).
  Sintesi operativa in `ricerche/opt-1080/00-PIANO-TEST.md` (33 test, 6 ondate). Nulla applicato.
- Scoperte principali: CUDA graph disabilitate da `ggml-cuda.cu:4231` (`cc < VOLTA`, la 1080 e' 610)
  confermato a runtime; 1516 kernel/token con `tau` ~12 us = 82% del tempo (banda solo 18%);
  GPU occupata al 70-77% (bolle di lancio); chiamate di servizio di Odysseus rubano
  100-200 s a turno (520 s di GPU per 0 memorie estratte); `--cache-ram 0` disattiva anche
  pulizia della KV; build ufficiale ha solo PTX per sm_61 (JIT).
- Strumento di misura A/B: `scripts/banco-1080.py` (scarta warmup, alterna A/B, guardie
  RAM/VRAM/temperatura, registra clock e utilizzo).
- Misure di oggi: contesto 131072 costa 850 MiB e **zero** velocita'; campionamento su 157k di
  vocabolario non costa nulla; nessuno spill VRAM->RAM; 35 tok/s erano warmup (reali 45-47).

## 24 ago 2026 — onda 0 (diagnostica) eseguita

Esiti in `ricerche/opt-1080/18-esiti-onda0.md`. Nessuna configurazione di produzione toccata.
- **1794 nodi per token**, 2 split, di cui **SPLIT #0 gira su CPU** (GET_ROWS dell'embedding).
- **Fusione dei kernel e' ATTIVA sulla 1080** (guard `cc <= 600`, noi 610): spegnerla costa
  −14,6% sul decode e −2,6% sul prefill → **ogni kernel in piu' costa 15-19 us**.
- **CUDA graph gia' spente** (D03 nel rumore); **riuso del grafo attivo** (spegnerlo −7,5%).
- **`expert_group_count=1` da' +30,2%**: 327 nodi del routing a gruppi costano il 30% del decode.
  Patch della fusione TopK-MoE diventa priorita' numero uno. `expert_used_count=4` da' +10,6%.
- **Verificare 4 token costa come verificarne 1** (24,9 vs 23,9 ms), gradino a 5 come previsto:
  speculativa con draft da 3 promossa a priorita' massima.
- **Throttling termico, non di potenza** (183→122 W mentre clock scende): power limit inutile,
  ventola/ripasta si'. Memoria a 4513 MHz anche sotto carico (stato P2).
- **Prefill server vs llama-bench: 1,23x, non 3,5x** (era artefatto di misura).
- **Difetto del riuso del prefisso**: dopo UNA richiesta intercalata, prompt esteso riusa 8
  token su 3007. `--cache-ram 2048` NON lo cura: serve separare slot o chiamate di servizio.
- Corretto `scripts/banco-1080.py`: prompt ora varia a ogni giro (prima falsava il pp).
