# PROVE: mercati-generale (mai iniettato; lo legge il revisore)

| affermazione nella skill | fonte (file:riga) | operazioni del banco |
|---|---|---|
| fin_mercati senza `titolo` da' il quadro generale: gruppi `difesa`, `tecnologia`, `cripto` con `prezzo` e `variazione_pct` | odysseus/src/shadowbroker/finanza.py:391-412 (`gruppo()`, `fuori = {"tipo":"mercati","difesa":difesa,"tecnologia":tech[:8],"cripto":cripto}`) | in attesa operazioni-finanza.json |
| `lettura_difesa.controcorrente`: titoli che vanno contro la media del proprio comparto | finanza.py:414-428 (`variazioni`, `media`, `contrarie`, `fuori["lettura_difesa"]`) | |
| `picchi`: i 3 movimenti piu' forti, con `ha_notizia` | finanza.py:454-462 (`picchi = sorted(tutti, key=lambda t: -abs(t["variazione_pct"]))[:3]`, `ha_notizia`) | |
| `picchi_senza_notizia`: nessuna notizia collegata, mai attribuire il movimento alla notizia di un altro titolo | finanza.py:463-468 (`fuori["picchi_senza_notizia"] = f"...mai attribuire il movimento a notizia di altro titolo..."`) | |
| `non_osservabile` quando il layer `stocks` e' vuoto: non significa mercati fermi | finanza.py:470-474 (`fuori["non_osservabile"] = "layer 'stocks' vuoto: fetcher non ancora girato o chiave assente. Non significa mercati fermi."`) | |
| le notizie qui coprono solo i ticker difesa/tech/cripto, non la geopolitica generale | finanza.py:439-451 (`notizie = dati.get("finnhub_news")`, ordinate per peso sui picchi di QUESTI gruppi); per la geopolitica generale serve un altro strumento (fuori da questa skill) | |
| i gruppi sono ordinati per `variazione_pct`, non per importanza della risposta | finanza.py:400 (`gruppo()`: `sorted(fuori, key=lambda x: -x["variazione_pct"])`), 456 (`picchi` ordinati per `abs(variazione_pct)`) | |

Token (verifica-skill.py, tokenizzatore GGUF LFM2.5): 293 iniettati, descrizione 21.
