# Changelog — integrazione capacità ShadowBroker (20 ago 2026)

Tutti 6 punti dal gap (`ricerche/gap-shadowbroker-capacita-non-considerate.md`).
Ogni tool segue checklist `aggiungi-tool-modello`. Banchi LLM rimandati (come da
regola: si fanno a caldo dopo).

| # | Feature | Stato | Note |
|---|---|---|---|
| 1 | `osint_geocode` (search+reverse) | ✅ | live: "Kyiv, Ukraine" risolto |
| 2 | `osint_cyber` (malware+KEV+country-risk) | ✅ | live: country-risk UA=100 |
| 3 | feed già-attivi nei briefing | ✅ | gps_jamming, ukraine_alerts, crowdthreat in allerte()+zona() |
| 4 | `osint_radio` (ACARS+scanner+KiwiSDR) | ✅ | live: scanner+geocode punto ok |
| 5 | `osint_satellite` on-demand (thermal+overflights) | ✅ | dispatch verificato (thermal/overflights lenti, non smoke) |
| 6 | watchdog proattivo nel loop | ✅ | `osint_sorveglianza azione=avvisi` + `osint_situazione` riferisce avvisi da solo |

**Verifica**: unit dispatch **27/27**, smoke live **4/4** (geocode, cyber×2, radio).
Intelligence 14→**18 tool** (indice semantico ne mostra ~8/turno).

## Dettaglio modifiche

### Nuovi tool (schemi.py + shadowbroker_tools.py)
- **`osint_geocode`** — `GET /api/geocode/search` (nome→coord), `/reverse` (coord→nome). Handler `GeocodeTool`.
- **`osint_cyber`** — `GET /api/malware` (abuse.ch C2), `/api/cyber-threats` (CISA KEV), `/api/country-risk`. Azioni malware/vulnerabilita/rischio_paese/tutto. Handler `CyberTool`.
- **`osint_radio`** — scanner (`/api/radio/nearest-list`), kiwisdr (`/api/sigint/nearest-sdr`), acars (`/api/aviation/datalink/messages`, euristica icao24/registration/callsign). Handler `RadioTool`.
- **`osint_satellite`** — termico (`/api/thermal/verify`), passaggi (`POST /api/satellites/overflights`, bbox calcolato da punto+raggio). Handler `SatelliteTool`.

### Client (client.py)
- `http_get` / `http_post` — endpoint HTTP diretti (non canale). Su loopback auth (compreso `require_local_operator`) bypassata.
- `avvisi_watchdog` — drena avvisi spinti dal watchdog via `POST /api/ai/channel/poll`.

### #3 — feed già attivi nei briefing (briefing.py)
- `allerte()`: caricati e portati a **voci** `gps_jamming`, `ukraine_alerts`, `crowdthreat` (prima solo dichiarati vuoti). firms_fires/internet_outages/space_weather erano già dentro.
- `LAYER_ZONA`: aggiunti gps_jamming, ukraine_alerts, crowdthreat.

### #6 — watchdog proattivo
- `osint_sorveglianza` azione **`avvisi`** → legge alert già spinti dal watchdog.
- `osint_situazione` (panoramica "cosa succede") **drena e riferisce** avvisi watchdog da sola (best-effort, timeout 6s, cache-neutrale: è output di tool, non prompt). Così emergono proattivamente ogni panoramica.
- Push background TOTALMENTE autonomo (senza turno utente) resta passo successivo: richiede poller Odysseus + canale notifica UI. Non toccato per non destabilizzare loop caldo.

### Regole (schemi.py REGOLE_OSINT)
- Ricette in positivo per geocode / cyber / radio / satellite.

### Registro / profili / TOOL_TAGS
- 4 nuovi sono `osint_*`: auto in `TOOL_TAGS` e in `OSINT_TOOL_NAMES` (Intelligence). Nessuno nel profilo Financial.

### Test (scripts/prova_facce_nuove.py)
- +12 verifiche dispatch (mock http_get/http_post/avvisi_watchdog + geo). Totale 27/27.

### Docs
- `VERGILIUS-FEATURES.md` (inventario completo, nuovo), `docs/knowledge/14-agente-osint.md`, questo changelog.

## Da fare (a caldo, dopo)
- Banchi LLM: aggiungere casi per 4 nuovi tool a `prova_modello_finanza`/`prova_e2e_agente` e girarli a modello caldo.
- Valutare se 18 tool in Intelligence confondono il 9B (bench lo dirà); eventualmente spostare geocode/cyber/radio/satellite dietro sotto-profilo.
- Push watchdog autonomo in background (poller + notifica UI).
