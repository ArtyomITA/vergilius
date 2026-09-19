# Attribuzioni

Vergilius integra e avvia due progetti indipendenti, entrambi distribuiti sotto
licenza GNU Affero General Public License v3.0. Le loro licenze e i loro avvisi di
copyright restano nelle rispettive cartelle e vanno mantenuti in ogni copia.

| componente | cartella | origine | licenza |
|---|---|---|---|
| Odysseus — l'assistente | `odysseus/` | https://github.com/odysseus-dev/odysseus (fork: https://github.com/ArtyomITA/odysseus) | AGPL-3.0 (`odysseus/LICENSE`) |
| ShadowBroker — l'intelligence | `shadowbroker/` | https://github.com/bigbodycobain/shadowbroker (fork: https://github.com/ArtyomITA/Shadowbroker) | AGPL-3.0 (`shadowbroker/LICENSE`) |

Vergilius (il loader `boot/`, gli script di avvio e configurazione, l'integrazione dei
due progetti e le ottimizzazioni documentate nel README) è distribuito sotto la stessa
licenza AGPL-3.0, come richiesto dalle licenze dei componenti.

## Software di terze parti richiesto ma non incluso

| cosa | dove si prende | licenza |
|---|---|---|
| llama.cpp / llama-server | https://github.com/ggml-org/llama.cpp | MIT |
| llama-swap | https://github.com/mostlygeek/llama-swap | MIT |
| ChromaDB | https://www.trychroma.com | Apache-2.0 |

## Materiale grafico di terzi incluso

| cosa | dove sta | autore | licenza |
|---|---|---|---|
| Modello Live2D di esempio "Niziiro Mao (PRO Version)" | `odysseus/static/live2d/mao_pro/` | Live2D Inc. (illustrazione e modellazione) | NON e' AGPL. Si usa accettando il "Free Material License Agreement" e i "Terms of Use" di Live2D: https://www.live2d.com/en/download/sample-data/ . Utenti comuni e piccole imprese possono usarlo anche a fini commerciali; gli altri soggetti solo per uso interno o di valutazione. Il file `ReadMe.txt` originale di Live2D sta nella stessa cartella. |
| Librerie Live2D Cubism Core e runtime | `odysseus/static/lib/` | Live2D Inc. e rispettivi autori | licenze proprie (Live2D Proprietary Software License per Cubism Core): vedi i file nella cartella |

Chi ridistribuisce Vergilius deve rispettare anche queste licenze. Per usare un personaggio
diverso basta sostituire la cartella del modello: il programma legge i parametri dal file
`model3.json`.

## Modelli

| modello | origine | licenza | uso in Vergilius |
|---|---|---|---|
| LFM2.5-2.6B | [LiquidAI/LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B), GGUF: [LiquidAI/LFM2.5-2.6B-GGUF](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF) | LFM Open License v1.0 (basata su Apache-2.0; uso commerciale libero sotto 10M USD di ricavi annui) | il modello predefinito, dal 19 set 2026 |
| LFM2.5-2.6B-DSpark | [LiquidAI/LFM2.5-2.6B-DSpark-GGUF](https://huggingface.co/LiquidAI/LFM2.5-2.6B-DSpark-GGUF) | LFM Open License v1.0 | drafter speculativo ufficiale del modello predefinito |
| Holo-3.1-0.8B | Hugging Face | vedi scheda modello | la vista (legge schermo e immagini) |
| QwenPaw-Flash-9B heretic | Hugging Face | vedi scheda modello | alternativa facoltativa, uncensored, scelta dall'utente |
| LFM2.5-2.6B-Uncensored (SC117) | Hugging Face | vedi scheda modello | alternativa facoltativa, uncensored, modificata da terzi (non release Liquid AI) |

I modelli non sono inclusi nel repository e non sono coperti da questa licenza: ognuno
ha la propria, che accetti scaricandoli con `scripts/scarica-modelli.py`.
