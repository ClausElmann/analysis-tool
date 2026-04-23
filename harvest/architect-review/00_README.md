# Architect Review Package — ServiceAlert → GreenAI

**Dato:** 2026-04-23  
**Kilde:** 630 VERIFIED + 89 INFERRED behaviors + 593 danske komponent-behaviors  
**Total:** 48 auto-genererede user stories + 10 forslag til manglende

---

## Filer i denne pakke

| Fil | Formål | Tid |
|-----|--------|-----|
| `01_gaps.md` | 5 kendte huller — kræver beslutning FØR build | ~10 min |
| `02_all_stories.md` | Alle 48 stories i tabeller — kode + ny-prio | ~20 min |
| `03_missing_stories.md` | 10 forslag til stories der mangler | ~5 min |
| `04_build_order.md` | Tom build-wave skabelon — udfyldes sidst | ~10 min |

**Anbefalet rækkefølge:** 01 → 02 → 03 → 04

---

## Hurtig status

| Kategori | Antal |
|----------|-------|
| Godkendte stories (GO) | 0 / 48 |
| Åbne beslutninger | 5 gaps + 48 stories |
| Foreslåede nye stories | 10 |
| Eksisterende GreenAI-features UDEN story | 3 |

---

## Hvad sker der EFTER review

Når arkitekten har markeret koderne og udfyldt `04_build_order.md`:

1. Copilot læser `04_build_order.md` → starter WAVE 1
2. Per story: `get_story_context.py --story "US-XXX"` henter dyb implementeringskontext
3. Copilot bygger vertical slice (Feature + Razor-side + SQL + test)
4. Byg → test → næste story

**Alt er 100% AI-bygget og AI-vedligeholdbart fremover.**

---

## Maskin-filer (til reference — ikke til redigering)

| Fil | Indhold |
|-----|---------|
| `harvest/unified/user_stories.json` | Alle 48 stories + behaviors (87 KB) |
| `harvest/unified/ui_manifest.json` | Blazor-side struktur (60 KB) |
| `harvest/unified/ui_masterplan.md` | Fuld UI-bibel med patterns (37 KB) |
| `harvest/unified/story_prompt_pack.md` | Mega-prompt til LLM-builder (53 KB) |
| `harvest/unified/behavior_pool.json` | 630+89+593 behaviors (392 KB) |
