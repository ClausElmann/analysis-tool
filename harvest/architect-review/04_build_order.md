# Build-rækkefølge (udfyldes af arkitekt)

Kopiér godkendte story-IDs hertil i den rækkefølge de skal bygges.
Copilot læser denne fil når den skal implementere næste story.

---

## WAVE 1 — Fundament (shared components + auth-sider)

Bygges ALTID først, blokkerer alt andet.

```
WAVE 1:
  - Shared/DataGrid/AppDataGrid.razor
  - Shared/Dialogs/ConfirmDeleteDialog.razor
  - Shared/Dialogs/BaseFormDialog.razor
  - NavigationMenu.razor (opdater med domæne-grupper)
```

**Status:** `[ ]` GODKENDT

---

## WAVE 2 — Kerne (arkitekt udfylder)

```
WAVE 2:
  [ ] US-???
  [ ] US-???
  [ ] US-???
```

**Note fra arkitekt:**

---

## WAVE 3 — Sekundær (arkitekt udfylder)

```
WAVE 3:
  [ ] US-???
  [ ] US-???
```

**Note fra arkitekt:**

---

## WAVE 4 — Nice-to-have (arkitekt udfylder)

```
WAVE 4:
  [ ] US-???
```

---

## DROP-liste (stories der IKKE bygges)

```
DROP:
  [ ] US-???  reason: ...
```

---

## Copilot-instruktioner (udfyldes når WAVE 2+ er godkendt)

Når arkitekten har udfyldt WAVE 2+, skriv her:

```
NÆSTE BUILD: US-XXX — [titel]
Kontekst: [evt. noter]
Afhænger af: [evt. andre stories]
```
