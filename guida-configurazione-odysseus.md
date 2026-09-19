# Guida alla personalizzazione di Odysseus

Riferimento pratico ricavato leggendo codice del checkout locale
(`d:\assistenteeee\odysseus`, branch `main`) più documentazione community.
Tutto senza toccare codice core.

---

## 1. Impostazioni

**Dove vivono**
- `data/settings.json` — impostazioni globali (solo admin).
- `data/features.json` — interruttori funzionalità: `web_search`, `web_fetch`,
  `deep_research`, `memory`, `document_editor`, `rag`, `sensitive_filter`, `gallery`.
- `data/user_prefs.json` — preferenze per utente (`{"_users": {"admin": {...}}}`).

Lista autorevole chiavi: `DEFAULT_SETTINGS` in `src/settings.py:31`. File
salvato fuso sopra i default: chiave assente = default. Cache di
2 secondi: modifica a mano si applica quasi subito, **senza riavvio**.

**Chiavi che contano**

| Tema | Chiavi |
|---|---|
| Modelli per ruolo | `default_endpoint_id`, `default_model`, `default_model_fallbacks`, `utility_*`, `vision_model`, `vision_enabled`, `research_endpoint_id`, `research_model`, `task_endpoint_id`, `task_model`, `teacher_model`, `image_model`, `image_gen_enabled` |
| Tuning agente | `agent_max_rounds` (20, limiti 1-200), `agent_max_tool_calls` (0 = illimitato), `agent_input_token_budget` (6000 = "auto"), `agent_input_token_hard_max` (200000), `agent_stream_timeout_seconds` |
| Skill | `skill_max_injected` (3, limiti 0-12), `skill_autosave_min_confidence` (0.85) |
| Ricerca | `search_provider`, `search_fallback_chain`, `search_result_count`, chiavi API provider |
| Deep research | `research_max_tokens`, `research_run_timeout_seconds` (1800), timeout vari |
| Voce | `tts_enabled`, `tts_provider`, `tts_voice`, `stt_enabled`, `stt_provider`, `stt_model`, `stt_language` |
| Reminder | `reminder_channel`, `reminder_llm_persona`, `reminder_ntfy_topic` |

**Admin contro utente.** Tutte chiavi di `settings.json` scritte solo da admin.
Sottoinsieme sovrascrivibile per utente (`_PER_USER_KEYS`, `src/settings.py:267`):
modelli default, utility, vision, immagini, research. Resto ignora
preferenza utente.

**Tre modi per cambiarle**
1. Interfaccia: ingranaggio in sidebar o `Ctrl+,`, oppure `/settings [tab]`.
2. API: `POST /api/auth/settings` (JSON, solo admin; accetta solo chiavi note).
   Per utente: `PUT /api/prefs/{key}` con `{"value": ...}`.
3. File: editare `data/settings.json`, rilettura entro 2 secondi.

Scorciatoia: esiste tool `manage_settings`. Puoi dire in chat "cambia canale
reminder in ntfy" e lo fa da solo. Chiavi API restano sola lettura.

---

## 2. Personalità (preset)

`src/preset_manager.py` legge e scrive `data/presets.json`. Campi preset:
`name`, `character_name`, `system_prompt`, `inject_prefix`, `inject_suffix`,
`temperature`, `max_tokens`, `enabled`.

- **Predefiniti**: `code_analyze` (temperatura 0.2), `brainstorm` (0.9), `reason` (0.3).
- **`custom`**: slot editabile, spento di default. **È qui che va personalità
  persistente.**
- **`user_templates`**: libreria personaggi salvati da cui caricare nello slot custom.

**Come dare personalità persistente**
1. Interfaccia: barra chat → `+` → **Prompt** → tab **Persona**. Compila nome e
   prompt di sistema, poi **Start**.
2. API: `POST /api/presets/custom` con `{"name", "system_prompt", "temperature",
   "max_tokens", "enabled": true, "inject_prefix", "inject_suffix"}`.
3. File: `data/presets.json`, chiave `custom`, con `"enabled": true`.

`POST /api/presets/expand` prende note grezze e le espande in prompt di 3-6 frasi
(nella UI è il pulsante Expand).

**Due dettagli importanti:**
- Prompt del preset **non sostituisce** quello di base: aggiunto come
  messaggio di sistema in testa. Prompt di base assemblato a runtime dalle
  sezioni dei tool, non esiste file di testo da editare.
- `inject_prefix`/`inject_suffix` **non** finiscono nel prompt di sistema: attaccati
  al testo del messaggio utente lato browser, solo a preset attivo.
- Slot `custom` è globale, non per utente.

---

## 3. Skill

Percorso: `data/skills/<categoria>/<nome>/SKILL.md`. Frontmatter YAML + corpo markdown.

Campi frontmatter: `name` e `description` (i due che finiscono nel prompt), più
`version`, `category`, `tags`, `platforms`, `requires_toolsets`, `status`
(`draft`|`published`), `confidence`, `source`, `created`.

Sezioni riconosciute nel corpo: `## When to Use`, `## Procedure`, `## Pitfalls`,
`## Verification`.

**Come entrano nel prompt — due livelli:**
- **Indice completo**: una riga per ogni skill (`nome — descrizione`), sempre presente.
  Per questo installarne centinaia strozza il contesto.
- **Top-N complete**: fino a `skill_max_injected` (default 3) iniettate per intero,
  scelte per rilevanza.

Modello può leggere procedura completa a richiesta con
`manage_skills action=view name=<nome>`.

API principali (`/api/skills`): `GET ""`, `POST /add`, `PUT /{id}` (per pubblicare:
`{"status":"published"}`), `GET|POST /{id}/markdown`, `POST /import-from-url`,
`POST /audit-all`.

Interfaccia: modale **Brain** in sidebar → tab Skills. Tab Settings dello stesso
modale ha auto-estrazione, auto-approvazione e numero massimo skill iniettate —
ma sono **preferenze per utente** con precedenza sulle globali omonime.
Se modifica globale "non fa effetto", colpevole è quasi sempre questo.

---

## 4. MCP

Aggiungere server: `POST /api/mcp/servers`, **form multipart**, solo admin.
Campi: `name`, `transport` (`stdio`|`sse`|`http`), `command` (per stdio),
`args` (stringa JSON array), `env` (stringa JSON object), `url` (per sse/http).

Tabella `McpServer` in `core/database.py:483` dentro `data/app.db`.

Altri endpoint: `GET /api/mcp/servers`, `GET /api/mcp/tools`,
`PATCH /api/mcp/servers/{id}`, `POST /api/mcp/servers/{id}/reconnect`,
`DELETE /api/mcp/servers/{id}`.

**Disabilitare singoli tool**: `PATCH /api/mcp/servers/{id}/tools` con
`{"disabled": ["nome_tool", ...]}`. Nella UI sono caselle per-tool nella scheda
server. Leva da usare se modello sceglie tool sbagliati.

Server integrati registrati da soli (`src/builtin_mcp.py`): `image_gen`, `memory`,
`rag`, `email`, più `builtin_browser` via npx. Si spegne tutto con
`ODYSSEUS_DISABLE_MCP=1`.

Interfaccia: Settings → **Integrations** → + Add Integration → MCP Tool Server.

---

## 5. Temi e aspetto

Tema non sta in Settings: è un modale a parte (icona tema in sidebar, o `/theme`).

Funziona con variabili CSS su `document.documentElement`, dichiarate in
`static/style.css`. Fondamentali: `--bg`, `--fg`, `--panel`, `--border`, `--red`.
Colori sintassi derivati automaticamente.

16 temi predefiniti, massimo 8 personalizzati salvati. Persistenza in localStorage
con copia sul server (`PUT /api/prefs/theme`) — quindi tema è **per utente**.

Font personalizzati: file `.woff2`/`.ttf`/`.otf` in `static/fonts/custom/`.

**CSS o JavaScript personalizzati: non supportati.** Non esiste meccanismo di
iniezione. Per andare oltre le variabili bisogna editare `static/style.css`, cioè
modificare il core.

Agente può cambiare tema da solo (azioni `set_theme` e `create_theme`): basta
chiederglielo in chat.

**Appearance** in Settings è altra cosa: solo visibilità elementi
interfaccia, tramite attributi `data-ui-key`.

---

## 6. Dove clicco

| Cosa | Percorso |
|---|---|
| Modelli per ruolo | Settings → AI Defaults |
| Giri massimi agente, limite tool | Settings → Agent Tools (admin) → card Agent |
| Tool integrati on/off | Settings → Agent Tools → Built-in Tools |
| Ricerca web | Settings → Search |
| MCP | Settings → Integrations → + Add Integration |
| Memoria e skill | modale Brain in sidebar |
| Personalità | barra chat → `+` → Prompt → Persona |
| Temi | icona tema in sidebar, o `/theme` |
| Avatar Live2D (nostro) | Settings → Appearance → card in fondo |

---

## Avvertenze verificate

- `agent_input_token_budget` e `agent_input_token_hard_max` **non hanno controlli
  nell'interfaccia**: solo API o file.
- `task_model` / `task_endpoint_id`: nessuna interfaccia.
- `teacher_model` / `teacher_enabled`: interfaccia è **codice morto**, cerca
  elementi che non esistono. Solo API o file.
- **Voce: pannello praticamente assente in questo build.** Scheda TTS in
  `index.html` nascosta di proposito, codice STT punta a elementi inesistenti.
  Chiavi esistono e sono scrivibili via API, ma non c'è interfaccia.
  (Rilevante per noi: TTS italiano andrà configurato via API o file.)
- Impostazioni skill nella modale Brain scrivono in `user_prefs.json` e vincono
  sulle globali.
- Nella cartella `docs/` non esiste documentazione sui temi.
