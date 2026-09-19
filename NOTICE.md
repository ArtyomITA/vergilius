# Attribuzioni

Vergilius integra e avvia due progetti indipendenti, entrambi distribuiti sotto
licenza GNU Affero General Public License v3.0. Le loro licenze e i loro avvisi di
copyright restano nelle rispettive cartelle e vanno mantenuti in ogni copia.

| componente | cartella | origine | licenza |
|---|---|---|---|
| Odysseus — l'assistente | `odysseus/` | https://github.com/pewdiepie-archdaemon/odysseus | AGPL-3.0 (`odysseus/LICENSE`) |
| ShadowBroker — l'intelligence | `shadowbroker/` | https://github.com/bigbodycobain/shadowbroker | AGPL-3.0 (`shadowbroker/LICENSE`) |

Vergilius (il loader `boot/`, gli script di avvio e configurazione, l'integrazione dei
due progetti e le ottimizzazioni documentate nel README) è distribuito sotto la stessa
licenza AGPL-3.0, come richiesto dalle licenze dei componenti.

## Software di terze parti richiesto ma non incluso

| cosa | dove si prende | licenza |
|---|---|---|
| llama.cpp / llama-server | https://github.com/ggml-org/llama.cpp | MIT |
| llama-swap | https://github.com/mostlygeek/llama-swap | MIT |
| ChromaDB | https://www.trychroma.com | Apache-2.0 |

## Modelli

| modello | origine | licenza | uso in Vergilius |
|---|---|---|---|
| LFM2.5-2.6B | [LiquidAI/LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B), GGUF: [LiquidAI/LFM2.5-2.6B-GGUF](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF) | LFM Open License v1.0 (basata su Apache-2.0; uso commerciale libero sotto 10M USD di ricavi annui) | il modello predefinito, dal 19 set 2026 |
| LFM2.5-2.6B-DSpark | [LiquidAI/LFM2.5-2.6B-DSpark-GGUF](https://huggingface.co/LiquidAI/LFM2.5-2.6B-DSpark-GGUF) | LFM Open License v1.0 | drafter speculativo ufficiale del modello predefinito |
| Holo-3.1-0.8B | Hugging Face | vedi scheda modello | la vista (legge schermo e immagini) |
| Ling-3.0-tiny | inclusionAI (Hugging Face) | vedi scheda modello | alternativa facoltativa (`--con-ling`), era il modello predefinito fino al 19 set 2026 |
| QwenPaw-Flash-9B heretic | Hugging Face | vedi scheda modello | alternativa facoltativa, uncensored, scelta dall'utente |
| LFM2.5-2.6B-Uncensored (SC117) | Hugging Face | vedi scheda modello | alternativa facoltativa, uncensored, modificata da terzi (non release Liquid AI) |

I modelli non sono inclusi nel repository e non sono coperti da questa licenza: ognuno
ha la propria, che accetti scaricandoli con `scripts/scarica-modelli.py`.
