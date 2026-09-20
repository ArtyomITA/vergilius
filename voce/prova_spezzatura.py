"""Prove dello spezzatore e della pulizia del ponte voce.

Niente pytest: asserzioni in chiaro, cosi' gira con qualunque python che
abbia le dipendenze del ponte.

    d:\\assistenteeee\\tts-venv\\Scripts\\python.exe voce\\prova_spezzatura.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ponte_voce import (LIMITE_PEZZO, LIMITE_PRIMO_PEZZO, pulisci_per_voce,
                        spezza_per_sintesi)

falliti = []


def prova(nome, condizione, dettaglio=""):
    if condizione:
        print(f"  ok   {nome}")
    else:
        falliti.append(nome)
        print(f"  NO   {nome}   {dettaglio}")


# -- spezzatura ---------------------------------------------------------

TESTO = (
    "Certo, ti riassumo la situazione. Il mercato di oggi si e' chiuso in "
    "leggero rialzo, trainato soprattutto dal settore tecnologico, mentre "
    "l'energia resta indietro. Leonardo LDO.MI ha chiuso a 1.541,19 euro con "
    "un guadagno del 3,5% e un volume di 2.300.000 pezzi, il massimo da marzo."
)

print("spezzatura")
pezzi = spezza_per_sintesi(TESTO)
prova("nessun pezzo oltre il limite",
      all(len(p) <= LIMITE_PEZZO for p in pezzi),
      str([len(p) for p in pezzi]))
prova("primo pezzo corto",
      len(pezzi[0]) <= LIMITE_PRIMO_PEZZO, repr(pezzi[0]))
prova("nessun pezzo vuoto", all(p.strip() for p in pezzi))
prova("nessun pezzo di sola punteggiatura",
      all(any(c.isalnum() for c in p) for p in pezzi))
prova("niente parole spezzate",
      " ".join(pezzi).replace(" ", "") == TESTO.replace(" ", ""),
      " ".join(pezzi))
for sigla in ("1.541,19", "3,5%", "LDO.MI", "2.300.000"):
    prova(f"{sigla} intero in un pezzo solo",
          any(sigla in p for p in pezzi), str(pezzi))

# Elenco senza punteggiatura: e' il caso che faceva 182 token.
ELENCO = " ".join(f"voce numero {n} dell'elenco" for n in range(1, 25))
pezzi_elenco = spezza_per_sintesi(ELENCO)
prova("elenco senza punteggiatura comunque tagliato",
      all(len(p) <= LIMITE_PEZZO for p in pezzi_elenco),
      str([len(p) for p in pezzi_elenco]))
prova("elenco: niente parole spezzate",
      " ".join(pezzi_elenco).replace(" ", "") == ELENCO.replace(" ", ""))

# Una parola sola piu' lunga del limite: si sfora, non si spezza.
LUNGA = "a" * 150
prova("parola lunghissima non spezzata", spezza_per_sintesi(LUNGA) == [LUNGA])

prova("testo vuoto", spezza_per_sintesi("") == [])
prova("sola punteggiatura", spezza_per_sintesi("... ;; --") == [])
prova("frase corta intera",
      spezza_per_sintesi("Fatto.") == ["Fatto."])

# Il primo pezzo si chiude alla prima clausola, se esiste.
p = spezza_per_sintesi("Ho controllato il calendario, domani mattina hai "
                       "due riunioni e la seconda e' subito dopo pranzo.")
prova("primo pezzo alla prima clausola",
      p[0] == "Ho controllato il calendario,", repr(p[0]))

# -- pulizia ------------------------------------------------------------

print("\npulizia")
prova("tag emozione via",
      pulisci_per_voce("[joy] Trovato!") == "Trovato!",
      repr(pulisci_per_voce("[joy] Trovato!")))
prova("tag con valore via",
      pulisci_per_voce("[emotion:happy] Ciao") == "Ciao",
      repr(pulisci_per_voce("[emotion:happy] Ciao")))
prova("tag maiuscolo via",
      pulisci_per_voce("[SAD] Ciao") == "Ciao")
prova("frase fra quadre non e' un tag",
      "nota" in pulisci_per_voce("Guarda [vedi la nota in fondo] qui"))
prova("tag tutto maiuscolo via",
      pulisci_per_voce("[TOOL_CALL] Fatto") == "Fatto")
prova("nome proprio fra quadre resta",
      "Milano" in pulisci_per_voce("Sede [Milano] centrale"),
      repr(pulisci_per_voce("Sede [Milano] centrale")))
prova("anno fra quadre resta",
      "2024" in pulisci_per_voce("Bilancio [2024] chiuso"))
prova("ragionamento chiuso via",
      pulisci_per_voce("<think>mmm</think>Ecco.") == "Ecco.")
prova("ragionamento aperto via",
      pulisci_per_voce("Ecco. <think>mmm e poi") == "Ecco.")
prova("blocco di codice via",
      pulisci_per_voce("Prima ```x = 1``` dopo") == "Prima dopo",
      repr(pulisci_per_voce("Prima ```x = 1``` dopo")))
prova("blocco di codice aperto via",
      pulisci_per_voce("Prima ```x = 1") == "Prima")
prova("indirizzo via",
      pulisci_per_voce("Vedi https://esempio.it/x qui") == "Vedi qui")
prova("link markdown: resta la scritta",
      pulisci_per_voce("Vedi [la borsa](https://x.it) qui") == "Vedi la borsa qui",
      repr(pulisci_per_voce("Vedi [la borsa](https://x.it) qui")))
prova("emoji via", pulisci_per_voce("Fatto \U0001F600 bene") == "Fatto bene")
prova("markdown via",
      pulisci_per_voce("**Titolo** e _corsivo_") == "Titolo e corsivo",
      repr(pulisci_per_voce("**Titolo** e _corsivo_")))
prova("numeri intatti",
      pulisci_per_voce("Sale a 1.541,19 euro, +3,5%") == "Sale a 1.541,19 euro, +3,5%",
      repr(pulisci_per_voce("Sale a 1.541,19 euro, +3,5%")))

# La catena intera: quello che fa davvero /v1/audio/speech.
print("\ncatena pulizia + spezzatura")
sporco = ("[joy] **Ecco il punto.** Leonardo LDO.MI a 1.541,19 euro, +3,5% "
          "oggi \U0001F680, vedi https://borsa.it/ldo per il resto.")
finale = spezza_per_sintesi(pulisci_per_voce(sporco))
prova("niente tag nei pezzi", not any("joy" in p for p in finale), str(finale))
prova("niente pezzi lunghi", all(len(p) <= LIMITE_PEZZO for p in finale),
      str([len(p) for p in finale]))
print("  pezzi:", finale)

print("\n%d prove fallite" % len(falliti))
sys.exit(1 if falliti else 0)
