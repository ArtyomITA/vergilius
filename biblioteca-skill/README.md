# Biblioteca di skill di Vergilius

Sorgenti versionate delle skill che Odysseus inietta da solo, in sottofondo, a seconda del compito (stanza 3,
emendamento del proprietario del 27 set 2026: libreria grande, tre cancelli, A/B per famiglia). Le skill non si
approvano una per una e il modello non se le costruisce: entrano solo da qui, dopo i tre cancelli.

## Fonti
- errori ricorrenti del banco d'uso (`scripts\banco-browser.py --scoperta`, file `candidati-TAG.md`);
- bozze nostre (`D:\vergilius-lab\ricerche\decisori\materiale-skill\`);
- framework scaricati (`skills-src\`): solo come struttura, RISCRITTE nel nostro formato con strumenti e parametri veri,
  mai importate cosi' come sono;
- sciame a ondate di 2 agenti: scrive in `D:\vergilius-lab\biblioteca-staging\<dominio>\<nome>\`, il LEAD sposta qui.

## Formato
`biblioteca-skill\<dominio>\<nome>\SKILL.md` (+ `PROVE.md` accanto, mai installato). Dominio = `category`
(browser, osint, finanza, pc, file, voce).
- frontmatter: `name` = nome della cartella, kebab di 2-6 parole italiane, mai simile a uno strumento; `description`
  italiana <= 25 token che dice QUANDO serve (e' l'opzione che legge il selettore); `tags` = parole dell'utente;
  `tools: [..]` = tutti e soli gli strumenti citati; `status: published`, `source: user`, `owner: admin`.
- corpo: `## When to Use` (una riga), `## Procedure` 3-7 passi in inglese con chiamate `strumento {"chiave":"valore"}`
  vere, ultimo passo `Check: ...`; `## Pitfalls` <= 3. Parte iniettata <= 300 token. Mai parole distintive delle
  operazioni di VERIFICA dei banchi.
- `PROVE.md`: ogni affermazione con file:riga e id delle operazioni di SVILUPPO.

## I tre cancelli (comandi dalla radice `D:\assistenteeee`)
1. **Statico, per tutte, gratis** (zero errori, nessun servizio):
   `odysseus\venv\Scripts\python.exe scripts\verifica-skill.py --operazioni-verifica scripts\operazioni-browser.json biblioteca-skill\browser`
   (per lo staging: la cartella dello staging al posto di `biblioteca-skill\browser`).
2. **Banco del selettore, pochi minuti** (stack acceso e fermo, solo `/completion`, slot 2):
   prima `odysseus\venv\Scripts\python.exe scripts\banco-selettore-skill.py --famiglia browser --dry-run`
   (niente rete: valida il dataset `scripts\banco-selettore-browser.json` e rende i prompt), poi lo stesso comando senza
   `--dry-run`. Con skill nuove dello staging: `--skill-dir D:\vergilius-lab\biblioteca-staging\browser`. Passa se il
   braccio S (o S') fa ACCENDI sulla meta' di verifica: iniezioni sbagliate <= 10%, iniezioni sui casi "nessuna" <= 10%,
   richiamo >= 60%, F1 sopra il Jaccard, latenza mediana <= 0,35 s e p90 <= 0,5 s con chat 8k, tetto superato <= 2%.
   Ripresa: `--riprendi <file.jsonl>`; metriche rifatte offline: `--riepiloga <file.jsonl>`.
3. **A/B per famiglia**:
   - installa la famiglia per la prova: `odysseus\venv\Scripts\python.exe scripts\installa-biblioteca.py --prova-famiglia browser`
     (copia in `odysseus\data\skills` tutte le skill del dominio che passano il cancello 1 e scrive
     `biblioteca-skill\.prova-in-corso.json`; `--prova` per vedere cosa farebbe; non sovrascrive mai una skill non sua);
   - stack acceso con `ODYSSEUS_SKILL_SELETTORE=1` e `ODYSSEUS_BENCH_SKILL_FIELD=1` in `vergilius.env`, PC libero;
   - `odysseus\venv\Scripts\python.exe scripts\banco-browser.py --ab-famiglia browser --tag F1` (blocchi A-B-B-A,
     `--cicli 2` se INCERTO, `--riprendi` dopo un'interruzione). A = `bench_skills=nessuna`, B = selettore acceso.
     Bersagli = operazioni di verifica con skill della famiglia; controlli = 3 di verifica senza (prima le negative).
   - referto `D:\vergilius-lab\ricerche\skill\banco-browser\verdetto-F1.md`: verdetto TIENI del piano e, per i turni
     peggiorati, quali skill erano state iniettate.
   - togli la prova: `odysseus\venv\Scripts\python.exe scripts\installa-biblioteca.py --togli-prova` (toglie esattamente
     i file copiati, mai altri).

## Dopo il verdetto
- **TIENI**: i nomi della famiglia vanno in `INSTALLATE.txt` (li scrive il LEAD), poi `--togli-prova` e
  `odysseus\venv\Scripts\python.exe scripts\installa-biblioteca.py` (installa solo cio' che e' in `INSTALLATE.txt` e
  passa il cancello 1; rieseguirlo ripristina le skill toccate da `manage_skills`).
- **SCARTA / INCERTO**: si tolgono dalla famiglia le skill indicate nel referto come sospette (peggioramenti, delta
  negativo, gravi), `--togli-prova`, di nuovo `--prova-famiglia`, e si ripete il banco.
- Ogni cambio di description o di skill di un dominio: di nuovo cancelli 1 e 2 di quel dominio prima di installare.

## Prove offline degli strumenti
`odysseus\venv\Scripts\python.exe scripts\prova-banchi-skill-offline.py` (nessuna rete, nessuna GPU, mai
`odysseus\data`: cartelle temporanee).
