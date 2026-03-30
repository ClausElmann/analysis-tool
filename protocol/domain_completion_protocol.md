# Domain Completion Protocol v1

Formål: køre autonom domæneanalyse, ét domæne ad gangen, med stop/start, selvkontrol og anti-loop.

## 1. Driftstilstand

Systemet må kun være i én af disse tilstande pr. domæne:

- `pending`
- `in_progress`
- `blocked`
- `stable_candidate`
- `complete`
- `abandoned`

Globalt må kun ét domæne have `in_progress` ad gangen.

## 2. Filer der styrer protokollen

- `domains/domain_state.json` — sand kilde for status
- `data/domain_memory.json` — AI-afledt hukommelse og evidens
- `data/domains/discovered_domains.json` — fundne domæner
- `data/domains/domain_priority.json` — byg/prioritetsrækkefølge
- `domains/<domain>/000_meta.json` ... `095_decision_support.json` — domæneoutput
- `data/run_log.jsonl` — append-only kørselshistorik

## 3. Startregel

Ved start skal motoren:

1. læse `domain_state.json`
2. vælge første domæne i prioriteringslisten som ikke er `complete` eller `abandoned`
3. hvis et domæne allerede er `in_progress`, genoptages det
4. hvis ingen findes, stop med status `ALL_COMPLETE`

## 4. Arbejdsloop pr. domæne

For valgt domæne køres følgende loop:

1. læs nuværende domænemodel
2. læs domænehukommelse
3. beregn gaps
4. vælg næste assets baseret på gaps
5. analyser assets
6. merge ny viden ind i domænemodellen
7. kør cross-analysis
8. opdater scores
9. persistér alt atomisk
10. afgør om domænet skal fortsætte, blokeres, markeres som kandidat eller færdigt

## 5. Scores

Hvert domæne skal have disse scores i `000_meta.json` og `domain_state.json`:

- `completeness_score` (0-1)
- `consistency_score` (0-1)
- `saturation_score` (0-1)
- `new_information_score` (0-1)
- `evidence_balance_score` (0-1)

## 6. Færdig-regel

Et domæne må kun markeres `complete` når alle er opfyldt:

- `completeness_score >= 0.95`
- `consistency_score >= 0.90`
- `saturation_score >= 0.95`
- `new_information_score < 0.01`
- mindst 3 uafhængige evidenstyper er brugt, hvor muligt
- ingen `high` gaps tilbage
- samme vurdering er observeret i 3 på hinanden følgende iterationer

Indtil da er domænet ikke færdigt.

## 7. Stable candidate

Hvis et domæne ser færdigt ud i én iteration, sættes det til `stable_candidate`, ikke `complete`.

Først efter 3 på hinanden følgende stabile iterationer må det blive `complete`.

## 8. Blocked-regel

Et domæne sættes til `blocked` hvis:

- næste 2 iterationer ikke giver nye assets med score over tærskel
- samme `high` gap står uændret i 3 iterationer
- systemet ikke kan finde nye kilder til at besvare domænets huller

Når et domæne er `blocked`, skal state forklare præcis hvorfor.

## 9. Anti-loop kontrol

Motoren må ikke køre i ring. Indbyg disse regler:

### Regel A — Asset cooldown
Et asset må ikke analyseres igen for samme domæne i samme stage, medmindre:
- asset hash er ændret
- eller AI specifikt har markeret evidensen som utilstrækkelig
- eller cross-analysis har åbnet en ny hypotese

### Regel B — Gap stagnation
Hvis samme gap-ID findes uændret i 3 iterationer, må motoren ikke fortsætte med samme asset-valgstrategi. Den skal:
1. skifte evidenstype
2. udvide søgetermer
3. eller markere domænet `blocked`

### Regel C — No-op iteration
Hvis en iteration giver:
- ingen nye entities
- ingen nye flows
- ingen nye rules
- ingen nye integrations
så tæller det som `no_op_iteration += 1`.
Ved 3 no-op iterationer i træk skal domænet enten:
- blive `stable_candidate`
- eller `blocked`

### Regel D — Contradiction first
Hvis cross-analysis finder `contradictions`, må systemet ikke fortsætte bredt. Det skal først bruge næste iteration på at afklare disse.

## 10. Evidensprioritet

Ved gap-søgning bruges denne prioritet:

1. `code_file`
2. `sql_table` / `sql_procedure`
3. `batch_job` / `event` / `webhook` / `background_service`
4. `work_items_batch`
5. `wiki_section`
6. `git_insights_batch`
7. `labels_namespace`
8. `pdf_section`

Hvis et gap handler om forretningsregler, vægtes `wiki_section` og `work_items_batch` højere.

## 11. Stop/start-regel

Motoren skal kunne stoppes når som helst.

Før stop skal den altid have:

- skrevet `domain_state.json`
- skrevet `domain_memory.json`
- skrevet alle ændrede domænefiler
- skrevet én linje til `data/run_log.jsonl`

Ved genstart må den aldrig begynde forfra. Den skal fortsætte fra state.

## 12. Krav til run_log

Hver iteration appendes som én JSON-linje:

```json
{"ts":"2026-03-30T18:21:00Z","domain":"identity_access","iteration":7,"status":"in_progress","selected_assets":12,"new_information_score":0.03,"completeness_score":0.89,"result":"continue"}
```

## 13. Domæneoutput der skal være stærkt nok

Et færdigt domæne skal mindst have meningsfuldt indhold i:

- `010_entities.json`
- `020_behaviors.json`
- `030_flows.json`
- `070_rules.json`
- `090_rebuild.json`
- `095_decision_support.json`

Hvis nogen af disse er tomme eller trivielle, må domænet ikke markeres `complete`.

## 14. Operatørkommandoer

Disse er de eneste kommandoer der behøves:

- `START` — start eller genoptag næste domæne
- `CONTINUE` — fortsæt aktivt domæne
- `STATUS` — vis nuværende domæne, score og resterende gaps
- `STOP` — stop sikkert efter current iteration
- `RESET DOMAIN <name>` — nulstil ét domæne
- `ABANDON DOMAIN <name>` — markér et domæne som bevidst fravalgt

## 15. Kort operatørprompt til Copilot

Brug denne korte prompt hver session:

"Følg Domain Completion Protocol v1. Læs current state. Genoptag aktivt domæne eller vælg næste højst prioriterede ufuldstændige domæne. Arbejd kun på ét domæne. Kør indtil iterationen er sikkert persisteret. Brug anti-loop reglerne. Markér aldrig et domæne complete før alle completion-regler er opfyldt i 3 på hinanden følgende iterationer. Returnér kun: domæne, iteration, score før/efter, lukkede gaps, resterende gaps, og næste kommando."

## 16. Definition of done for hele systemet

Systemet er færdigbehandlet når:

- alle domæner i `domain_priority.json` er enten `complete` eller `abandoned`
- ingen domæner står som `in_progress` eller `stable_candidate`
- alle `complete` domæner opfylder completion-reglen
- `data/run_log.jsonl` dokumenterer forløbet

