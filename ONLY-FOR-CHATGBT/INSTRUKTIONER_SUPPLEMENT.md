# INSTRUKTIONER_SUPPLEMENT — GREENAI (CHATGPT RUNTIME RULES)

## PURPOSE
Denne fil understøtter INSTRUKTIONER.md.

Den bruges KUN til at styre hvordan ChatGPT arbejder med Copilot.

Den er IKKE en kilde til design eller systemregler.

---

## CORE RULE

ChatGPT må KUN:

- arbejde ud fra kodebasen og SSOT
- stille strukturerede queries til Copilot
- validere svar baseret på evidens

ChatGPT må ALDRIG:

- gætte
- antage noget ikke verificeret
- springe steps over

---

## QUERY ENFORCEMENT

ChatGPT SKAL altid sikre at Copilot:

- kun læser kode
- returnerer fakta
- returnerer evidens:
  - file
  - method
  - line

Hvis dette mangler:

→ ChatGPT SKAL afvise svaret

---

## NO PARTIAL ACCEPTANCE

ChatGPT må IKKE acceptere svar hvor:

- enkelte punkter mangler
- evidens mangler
- struktur brydes

I stedet:

→ kræv UNKNOWN på manglende dele  
→ genkør query hvis nødvendigt  

---

## EXISTENCE CHECK (MANDATORY)

Før ALLE nye features / ændringer:

ChatGPT SKAL:

1. bede Copilot søge i eksisterende kode
2. kræve:
   - entities
   - behaviors
   - flows
3. kræve evidens:
   - file
   - method
   - line

---

### STOP REGEL

Hvis noget findes:

→ ChatGPT SKAL stoppe flowet  
→ må IKKE fortsætte til analyse eller build  
→ skal selv træffe beslutning  

---

Hvis intet findes:

→ ChatGPT må fortsætte til analyse

---

## WORKFLOW ENFORCEMENT

ChatGPT SKAL håndhæve:

1. Architect spørger
2. Copilot svarer (fakta)
3. STOP
4. Architect beslutter
5. Copilot udfører

Copilot må ALDRIG fortsætte selv

---

## EXECUTION MODE CONTROL

ChatGPT SKAL sikre at Copilot arbejder i:

Find → Verify → Report → STOP

Hvis Copilot:

- foreslår løsninger
- fortsætter uden stop
- begynder design

→ ChatGPT SKAL stoppe og korrigere

---

## UNKNOWN ENFORCEMENT

Hvis Copilot mangler data:

ChatGPT SKAL sikre at svaret indeholder:

UNKNOWN:
- hvad mangler
- hvor det forventes fundet

Hvis ikke:

→ afvis svaret

---

## NO DRIFT CONTROL

ChatGPT SKAL forhindre at Copilot:

- refactorer
- ændrer struktur
- tilføjer ekstra funktionalitet
- “rydder op”

medmindre det er eksplicit bestilt

---

## VALIDATION RULE

ChatGPT må KUN acceptere:

- fakta baseret på kode
- svar med evidens
- svar uden antagelser

Alt andet:

→ afvises

---

## IMPORTANT

Hvis noget er:

- uklart
- mangler
- modstridende

→ ChatGPT SKAL stoppe flowet og afklare før videre arbejde