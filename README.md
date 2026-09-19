# Vergilius

**Un assistente che vive sul tuo computer, legge il mondo e non chiede il permesso a nessuno.**

Vergilius mette insieme tre cose che di solito stanno separate: un modello linguistico
che gira sulla tua scheda video, una raccolta di fonti aperte per capire cosa sta
succedendo nel mondo, e un'interfaccia che le tiene insieme. Nessuna chiave API verso
un fornitore di intelligenza artificiale, nessuna conversazione che esce dal computer,
nessun abbonamento.

È pensato per **macchine modeste**. Il modello predefinito, LFM2.5-2.6B di Liquid AI
(con drafter speculativo ufficiale DSpark), su una GeForce GTX 1080 del 2016 genera 64
token al secondo in decodifica, fino a 78-100 con il drafter attivo. Se hai una scheda
con 8 GB di memoria video, Vergilius gira.

---

## Cosa sa fare

**Capire cosa succede.** Notizie per soggetto e per luogo, mercati, contratti militari,
movimenti degli insider, mappe, archivio storico degli eventi. Le fonti sono aperte e
interrogabili: l'assistente le chiama da solo quando la domanda lo richiede.

**Lavorare sul tuo computer.** File, terminale, browser, documenti, note, calendario,
attività programmate. Con il modello di visione può leggere lo schermo.

**Ricordare.** Memorie, documenti indicizzati, procedure che impara e riusa.

**Dire quando non sa.** Questa parte è costata più lavoro di tutte le altre: un modello
piccolo, se non ha il dato, tende a inventarlo con sicurezza. Vergilius controlla che i
numeri e i nomi nella risposta compaiano davvero nei risultati degli strumenti, e se non
ci sono rilancia la risposta chiedendo di dirlo apertamente. Misurato: le cifre non
supportate scendono da 3 turni su 35 a 1 su 36.

---

## Come si avvia

Serve Windows con Python 3.12, Node.js, e una GPU NVIDIA con almeno 8 GB (funziona anche
solo su CPU, più lentamente).

```
git clone <questo repository> vergilius
cd vergilius
python scripts/scarica-modelli.py      # ~4,2 GB, una volta sola (--con-ling per il modello alternativo)
AVVIA-VERGILIUS.bat                    # doppio click
```

Si apre una pagina con quattro profili — scegli quello che ti serve:

| profilo | cosa accende |
|---|---|
| **ShadowBroker** | solo la parte di raccolta e analisi delle fonti |
| **Vergilius Chat** | solo l'assistente, senza le fonti |
| **Lite** | assistente + fonti, senza voce e avatar |
| **Full** | tutto, compresi voce e avatar |

Al primo accesso l'utente è `admin` con password `admin`: te lo ricorda la schermata di
login, e puoi cambiarla dalle impostazioni.

---

## Com'è fatto

```
    AVVIA-VERGILIUS.bat
            │
     boot/  ├── pagina dei profili (porta 7001)
            │
            ├── llama-swap ──── llama.cpp ──── il modello sulla GPU
            │                                  (LFM2.5-2.6B, e la vista su CPU)
            ├── ChromaDB ────── memorie e documenti indicizzati
            │
            ├── odysseus/ ───── l'assistente: chat, strumenti, agente (porta 7000)
            │
            └── shadowbroker/ ─ le fonti: raccolta, analisi, mappa (porta 3000)
```

Due progetti indipendenti, entrambi sotto licenza AGPL-3.0, che Vergilius integra e
avvia insieme:

- **[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus)** — l'assistente
- **[ShadowBroker](https://github.com/bigbodycobain/shadowbroker)** — l'intelligence

---

## Le impostazioni

Due file, separati apposta:

- **`vergilius.env`** — scelte che valgono su qualsiasi macchina: quanto può ragionare
  il modello prima di chiamare uno strumento, come viene riusata la cache della
  conversazione, le regole contro le risposte inventate. Ogni riga ha in commento la
  misura che la giustifica.
- **`vergilius-hardware.env`** — scelte tarate su una GPU precisa (nel repository c'è
  il profilo di una GTX 1080). Se hai un'altra scheda, cancellalo: il programma funziona
  lo stesso, e quelle righe le ritari quando vuoi.

Chi vuole andare a fondo: `scripts/vergilius-binario-pascal.ps1` accende i grafi CUDA
sulle schede Pascal, che llama.cpp tiene spenti per una regressione misurata nel 2024 su
un tipo di modello diverso. Sulla nostra architettura valgono il 40% di velocità in più,
con risposte identiche carattere per carattere ([PR
ggml-org/llama.cpp#27721](https://github.com/ggml-org/llama.cpp/pull/27721)).

---

## Licenza

AGPL-3.0, come i due progetti che integra. In pratica: puoi usarlo, studiarlo,
modificarlo e ridistribuirlo; se lo offri ad altri come servizio in rete, devi
pubblicare le tue modifiche.
