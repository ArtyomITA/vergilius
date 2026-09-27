# PROVE: insider-difesa (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| fin_insider accetta `titolo`, `quanti`; sei contractor validi RTX, LMT, NOC, GD, BA, PLTR | odysseus/src/shadowbroker/schemi.py:525-540 (schema); finanza.py:50 (`DIFESA`) | in attesa operazioni-finanza.json |
| `sentimento_mensile`: `mspr` da -100 a +100, gia' un rapporto che satura, con `azioni_nette` | finanza.py:682-688 (docstring MSPR), 694-705 (`sentimento.append({"titolo":s,"nome":...,"mese":...,"mspr":...,"azioni_nette":v.get("change")})`) | |
| ordinamento per `forza_segnale` = \|MSPR\| pesato sul logaritmo delle azioni, non per MSPR nudo | finanza.py:709-728 (`forza()`, commento: "MSPR satura... il logaritmo evita che la sola dimensione schiacci il rapporto"), 757 (`"ordinamento": "per forza del segnale..."`) | |
| `movimenti_recenti` e' relativo a UNA sola azienda, `movimenti_su`, anche quando `titolo` e' omesso | finanza.py:730-733 (`bersaglio = simboli[0] if titolo else (sentimento[0]["titolo"] if sentimento else DIFESA[0])`), 760 (`"movimenti_su": bersaglio`) | |
| codice `P`/`S` sono le uniche decisioni di mercato vere; `A`/`M` sono assegnazioni o esercizi a prezzo zero/prefissato | finanza.py:670-679 (`CODICI`, `DECISIONI_VERE = ("P","S")`), 744 (`"decisione_di_mercato": codice in DECISIONI_VERE`), 762-766 (`"nota_codici": "solo P e S = decisioni di mercato. A, M = assegnazioni ed esercizi... contarli come acquisti inverte il segnale."`) | |
| un `titolo` fuori dai sei e' scartato in silenzio: torna l'elenco di tutti e sei | odysseus/src/agent_tools/shadowbroker_tools.py:693-702, in particolare 697-698 (`if titolo and str(titolo).upper() not in finanza.DIFESA: titolo = None`) | |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 296 iniettati, descrizione 19.
