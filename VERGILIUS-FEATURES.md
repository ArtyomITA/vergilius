# Vergilius — tutte le features

Inventario completo di cosa fa Vergilius: assistente locale che unisce
**Odysseus** (workspace, riscritto), **ShadowBroker** (intelligence OSINT,
innestata) e un cervello locale, orchestrati su misura.
Gira per intero su una macchina sola: **nessun dato esce, nessuna chiave a pagamento,
nessun contenitore, nessun servizio esterno da cui dipendere.**

> Aggiornato: 20 ago 2026, cervello descritto sotto era **QwenPaw 9B**, superato
> prima da **Ling-3.0-tiny** (22 ago) poi dal predefinito attuale
> **LFM2.5-2.6B** (19 set 2026, vedi
> `odysseus/website/knowledge/02-modello-e-hardware.md` e
> `odysseus/website/knowledge/10-decisioni-e-alternative-scartate.md`). Resto
> della pagina non riscritto: descrive l'architettura al 20 ago. Per gap
> ancora da integrare vedi
> `ricerche/gap-shadowbroker-capacita-non-considerate.md`. Per ciclo agente
> `odysseus/docs/knowledge/19-loop-agente.md`.

---

## 0. La formula

```
Vergilius = Odysseus (riscritto)  +  ShadowBroker (innestato)  +  QwenPaw 9B  +  Orchestrazione
```

(cervello nella formula era QwenPaw 9B al 20 ago; predefinito attuale è LFM2.5-2.6B, vedi nota in cima)

- **Odysseus**: workspace open da cui partiamo — interfaccia, ciclo agente, memoria, competenze, strumenti. Riscritto nel profondo (loop, profili, ponte).
- **ShadowBroker**: piattaforma intelligence OSINT con 60+ feed. Innestata: mappa non si guarda, si interroga a voce.
- **QwenPaw 9B**: cervello locale, in due anime (standard + uncensored).
- **Orchestrazione**: loop, profili, ponte non-stream, compressione dati — costruiti da noi.

---

## 1. Il cervello — QwenPaw 9B (superato, vedi nota in cima: predefinito ora LFM2.5-2.6B)

- **Modello principale**: `QwenPaw-Flash-9B.i1-Q4_K_M.gguf` (5,24 GiB, Apache 2.0). Finetune di Qwen3.5-9B addestrato da AgentScope **per gli agenti** (strumenti, terminale, filesystem, ricerca multi-passo).
- **Anima uncensored**: `QwenPaw-Flash-9B-heretic-Q4_K_M.gguf` (ablazione livelli 13-16). Per compiti dove un falso allarme fermerebbe l'agente. Si sceglie dal menu.
- **Vista**: proiettori `mmproj-Q8_0` + `mmproj-heretic-BF16` — traducono immagini in token, **su RAM invece che sulla scheda** (~900 MB VRAM liberati, contesto con vista 32K).
- **48K di contesto** dentro 8 GB, grazie a: attenzione lineare (solo 8 livelli su 32 accumulano cache), flash attention anche su GPU 2016, cache compressa senza perdita, zero offload.
- **Q4_K_M con matrice d'importanza**: quantizzazione più spinta che mantiene perfetta chiamata a strumento (sotto IQ4 il JSON si incrina).
- **Motore**: llama.cpp + **llama-swap** (scambio profili automatico, cache KV vive su :5802).

## 2. Odysseus — il workspace

### 2.1 Il ciclo dell'agente
- Riceve → sceglie strumenti → chiama → legge → richiama → risponde. Fino a **20 giri/turno**.
- **Bilancio ingresso 40.000 token** (era 6.000: troncava il system prompt).
- **Supervisore d'intento** (bilingue, futuri italiani compresi): se annuncia azione e non la fa, giro dopo chiamata è **imposta dalla grammatica** (`tool_choice: required`, max 3 solleciti).
- **Ponte non-stream** per tool locali: tool call dei modelli con thinking viaggiano su richiesta dedicata (streaming le perdeva).
- **Registro auto-derivato** (`TOOL_TAGS`): tool nuovo con prefisso `osint_`/`fin_` riconosciuto in tutta la catena appena esiste.
- **Temperatura per fase**: ≤0,25 quando sceglie strumenti, voce del preset quando racconta.
- **Memoria delle tracce riuscite** (`tracce_agente.py`): turni buoni registrano domanda+sequenza; alla domanda simile sequenza riproposta in coda al messaggio utente (mai nel system: cache KV).
- **Cache KV per progetto**: prefisso stabile, compattazione una volta sola all'85%.

### 2.2 Memoria e DB vettoriale
- **ChromaDB** (embedding su CPU, host 127.0.0.1:8100): memoria semantica fra conversazioni + recupero dai documenti caricati (RAG).
- Odysseus **espone propria memoria come server MCP**: altri agenti possono leggerla.
- **Archivio finanziario** su collezione ChromaDB separata `financial_rag` (vedi §4.4).

### 2.3 Competenze (skills)
- **14 moduli** di istruzioni in **5 categorie**, iniettati **solo quando pertinenti** (max 3/turno) invece di stare sempre nel prompt.

### 2.4 Selezione semantica degli strumenti
- Indice a embedding recupera solo strumenti rilevanti fra **oltre 100** disponibili (compresi MCP). Al modello arrivano **~8 + 3 fissi** per turno.

### 2.5 Le mani — controllo del computer
- **Windows-MCP** (CursorTouch, stdio, 13 strumenti su 20): legge **albero di accessibilità** (testo, non fotografia). Cataloghi e osservazioni compressi (~40%).
- **Playwright MCP** (profilo isolato, capacità visive spente): lavoro ripetibile su molte pagine; riferimenti testuali > coordinate per un 9B.
- Scoperta: fotografia dell'albero passa dalle API di accessibilità → legge **tuo browser già autenticato senza aprire porte di debug**.

### 2.6 Ricerca approfondita
- Ricerca multi-passo vera (scompone, cerca, legge, verifica, ripete). Sul profilo **heretic** non si ferma a metà per argomento spinoso.
- **Mai a mani vuote**: se non trova, allarga match, propone ricerca più profonda, consegna comunque tutto dichiarando limiti.

### 2.7 Due profili dedicati
- **Intelligence** (14 tool) e **Financial** (8 tool). Aperto un profilo dotazione si restringe; ricerca web resta a bordo.

### 2.8 Voce — ciclo senza attese
- **ASR**: `nvidia/nemotron-3.5-asr-streaming-0.6b` (sherpa-onnx, 320 ms, int8): 40 lingue, **0 VRAM** (680 MB RAM), 2× il parlato. Fine turno automatica (nessun pulsante).
- **TTS**: `Kyutai PocketTTS 2.1` italiano (voce «estelle», int8, 234 MB RAM, 26 voci italiane), su CPU.
- **Avatar** Live2D Cubism 4 («Niziiro Mao», PixiJS): opzionale; labiale legge ampiezza dell'audio vero, parametri bocca dal personaggio stesso.
- Ponte voce :8013, PocketTTS :8014. ~2/3 della latenza tolta per architettura, non hardware.

### 2.9 Grafici
- Modello emette fence ```` ```chart ```` con JSON; `markdown.js` lo incapsula, `charts.js` lo disegna su canvas con **Chart.js ospitato in casa** (no CDN).

### 2.10 Indice strumenti (widget, 20 ago)
- Pulsante **🧰 Strumenti** sempre presente (alto-destra): indice a **3 livelli** Categoria → tool grande (spiega come chiama gli altri) → sotto-tool. Copre tutta piattaforma (~100 comandi). Dati da `catalogo-facce.json`, route `GET /api/shadowbroker/strumenti`.

### 2.11 Pulsante spegni-tutto (20 ago)
- ⏻ nella barra utente: `POST /api/vergilius/spegni` → script `spegni-tutto.ps1` (kill per albero) → Odysseus esce da solo. Riaccensione: `AVVIA-VERGILIUS.bat` / `scripts\avvia-tutto.ps1`.

## 3. Le mani sul PC (dettaglio MCP)
- Windows-MCP e Playwright MCP come sopra; assi indipendenti. Domanda vera per ogni compito: qual è rappresentazione più economica dello stato?

## 4. ShadowBroker — l'intelligence

### 4.1 La piattaforma
- Mappa mondiale, **60+ feed** che si aggiornano da soli. Gira nativa, incorniciata in iframe dentro Odysseus (CSP: rotte passano da `shadowbroker_routes.py`).
- Stili mappa (infrarosso, visione notturna), barra contatori live.

### 4.2 Il canale OpenClaw — ~97 comandi
- Canale agentico `POST /api/ai/channel/command` (+`/batch`, `/poll`, `/sse`, `/ws`). In **loopback auth bypassata**; **tier è `full`** (sblocca scritture: pin, watch, snapshot, inject).
- Manifest auto-descrittivo `/api/ai/tools`, router deterministico `route_query`, playbook nominati (`run_playbook`).
- Famiglie: mappa/display (pin CRUD, layer, imagery, analysis zones, inject), interrogazione (summary/report/brief_area/entities_near/what_changed/layer_slice), entità (find_flights/ships/entity, profile, trail, correlate, expand), news, OSINT/recon (osint_lookup 12 sotto-tool + sweep), rischio GT, watchdog, Time Machine, SAR, mesh/Infonet.

### 4.3 I nostri tool OSINT (14) + finanza (4)
- **Facciate** che chiamano comandi OpenClaw e **comprimono** per contesto minuscolo del 9B (grezzo = 47.891 token = 97% finestra):
  - `osint_situazione`, `osint_notizie` (assorbe testo articoli via url/id), `osint_militare`, `osint_allerte`, `osint_zona`, `osint_dettaglio`, `osint_cerca`, `osint_recon`, `osint_mappa`, `osint_web`, `osint_rischio` (GT), `osint_sorveglianza` (watchdog), `osint_storico` (Time Machine).
- **Finanza** (nostra, upstream non l'ha): `fin_mercati`, `fin_appalti`, `fin_insider`, `fin_archivio`.

### 4.4 Profilo Financial
- Preset entro tetto Finnhub 60 chiamate/min: **Core 25** (ogni min), **Broad 60** (ogni 2 min), **Deep news** (30 titoli, 7gg), **tempo quasi reale** (10 titoli, 30s). Popup che ricompare a ogni attivazione.
- **MSPR**: acquisti insider netti del mese, normalizzati −100..+100.
- **Contratti sulla mappa**: spesa federale ha luogo di esecuzione (Finnhub usa-spending).
- **fin_archivio / financial_rag**: archivio storico (ChromaDB) che conserva notizie, picchi, contratti, insider al passaggio; giro di fondo ogni 10 min; avvisa oltre 2.800 MB RAM / 20k doc e propone compressione (digest >30gg, purga >90gg).
- **Financial map mode**: pannello Market Wire, news finanziarie con "sulla mappa".
- Preset mappa financial volutamente magro: `gdelt · news · finnhub_news`.

### 4.5 Le classifiche già calcolate
- **threat_level** (0-100, 7 componenti, motivazioni in chiaro), **correlations** (eventi cross-fonte), **Plane-Alert** (16.077 immatricolazioni, 53 categorie), **gt_risk** (rischio per regione).

### 4.6 Reti e ricevitori pubblici
- **Meshtastic** (mesh LoRa, nodi che si dichiarano via MQTT), **KiwiSDR** (ricevitori 0-30 MHz nel browser, TDoA), **PSK Reporter** (propagazione), **Infonet** (mesh interna, vuota/su-invito), **Shodan** (dispositivi esposti, manuale). Fix del fetcher KiwiSDR: 798 congelati → 833 live.

## 5. Configurazione e chiavi
- `OPENCLAW_ACCESS_TIER=full` (sempre). `FINNHUB_API_KEY`, `SHODAN_API_KEY` configurate; mancano Sentinel Hub, NASA Earthdata, GFW.
- `agent_input_token_budget=40000`. Env: `ODYSSEUS_LOCAL_TOOLS_NONSTREAM`, `ODYSSEUS_LLM_DUMP`, `FIN_RAG_RAM_MB`.

## 6. Mappa architetturale (per noi che sviluppiamo)
- `architecture-map/`: CLI `arch` (locate/context/impact/changed/scan), viewer :8765, MCP read-only (7 tool). 31 gruppi, 88 componenti, 25 archi cross-repo. `arch impact` = blast radius, anche fra i due repo.

## 7. Stack e porte
| Servizio | Porta |
|---|---|
| Odysseus | 7000 |
| ShadowBroker frontend | 3000 |
| ShadowBroker backend | 8000 (+ wormhole 8787) |
| ChromaDB | 8100 |
| ponte voce / PocketTTS | 8013 / 8014 |
| llama-swap / llama-server | 8012 / 5802 |
| architecture viewer | 8765 |

Avvio: `AVVIA-VERGILIUS.bat` o `scripts\avvia-tutto.ps1`. Spegnimento: pulsante ⏻ o `scripts\spegni-tutto.ps1`.

## 8. Test
- Doppio banco: `prova_modello_finanza.py` (scelta strumento), `prova_e2e_agente.py` (loop vero attraverso API). Unit `prova_facce_nuove.py`. Ultimo verde: 17/17 diretto, 4/4 E2E.

## 9. Cosa NON fa ancora (scoperte da integrare)
Vedi `ricerche/gap-shadowbroker-capacita-non-considerate.md`. In lavorazione (20 ago): geocoding, `osint_cyber`, feed già-attivi nei briefing, `osint_radio`, analisi satellitari on-demand, watchdog proattivo. Da ignorare: mesh/Infonet/wormhole/privacy-core/desktop (irrilevanti in locale).

---

## Changelog features (20 ago 2026)
- Fusione `osint_testo` → `osint_notizie`; 3 facciate nuove (`osint_rischio`/`osint_sorveglianza`/`osint_storico`); tier `full`; indice strumenti a 3 livelli; pulsante spegni-tutto; route `/vergilius/spegni` e `/shadowbroker/strumenti`.
- In corso: 6 punti del gap (vedi `CHANGELOG-vergilius-feature-20ago.md`).
