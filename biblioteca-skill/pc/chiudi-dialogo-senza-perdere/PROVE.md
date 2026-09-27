# PROVE: chiudi-dialogo-senza-perdere

| affermazione nella skill | fonte (file:riga) | operazioni |
|---|---|---|
| "Ok/Si/Yes/Continua/Procedi/Accetta/Applica" contano irreversibili come prima parola dell'etichetta, dentro un dialogo o se non si sa | odysseus/src/tool_execution.py:1040-1043 (`_CONFERME_DI_DIALOGO`), 1155-1162 (`_etichetta_irreversibile`) | P12 |
| "non salvare" / "don't save" / "dont save" / "do not save" sono frasi sempre irreversibili, qualunque sia il dialogo | odysseus/src/tool_execution.py:1032-1037 (`_FRASI_IRREVERSIBILI`), 1159 (`_contiene_frase`) | P10 |
| "Annulla"/"Cancel"/"No" non compaiono ne' nei verbi irreversibili ne' nelle conferme di dialogo: il classificatore non li segna irreversibili | odysseus/src/tool_execution.py:1007-1045 (`_RE_VERBI_IRREVERSIBILI`, `_FRASI_IRREVERSIBILI`, `_CONFERME_DI_DIALOGO`: nessuno contiene annulla/cancel/no), 1355-1358 (uso in `azione_desktop_irreversibile`) | P10 (percorso alternativo sicuro) |
| Shortcut "escape" non e' fra i tasti sempre irreversibili ne' rientra nel ramo spazio/lettera-singola dentro un dialogo: non chiede approvazione | odysseus/src/tool_execution.py:1101 (`_TASTI_SEMPRE_IRREVERSIBILI`, "escape" assente), 1247-1267 (`_shortcut_irreversibile`) | nessuna (fatto di codice, motiva il passo 2) |
| vista_schermo con `focus` mirato al dialogo ritorna titolo e pulsanti nella descrizione + albero_ui | odysseus/src/vista/schemi.py:11-28 | P10, P12 |

Token: da misurare con verifica-pc.py.
