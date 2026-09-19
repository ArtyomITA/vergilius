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

I modelli non sono inclusi nel repository e non sono coperti da questa licenza: ognuno
ha la propria, che accetti scaricandolo.

| modello | origine | uso in Vergilius |
|---|---|---|
| Ling-3.0-tiny | inclusionAI (Hugging Face) | il modello predefinito |
| Holo-3.1-0.8B | Hugging Face | la vista (legge schermo e immagini) |
| QwenPaw-Flash-9B heretic | Hugging Face | alternativa facoltativa, scelta dall'utente |
