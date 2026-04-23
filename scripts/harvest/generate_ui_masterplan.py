#!/usr/bin/env python3
"""
generate_ui_masterplan.py — User stories → Blazor UI-bibel

Læser:
  harvest/unified/user_stories.json

Skriver:
  harvest/unified/ui_manifest.json      (maskin-læsbar app-struktur)
  harvest/unified/ui_masterplan.md      (AI build bible — rød tråd, navigation, patterns)
  harvest/unified/story_prompt_pack.md  (mega-prompt til LLM der skal bygge UI)

Usage:
  python scripts/harvest/generate_ui_masterplan.py
  python scripts/harvest/generate_ui_masterplan.py --dry-run
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

OUT_DIR = Path("harvest/unified")
USER_STORIES_PATH = OUT_DIR / "user_stories.json"

# ──────────────────────────────────────────────────────────────────
# SHARED PATTERNS (rød tråd)
# ──────────────────────────────────────────────────────────────────
SHARED_PATTERNS = """
## Delte UI-mønstre (ALLE sider følger disse)

### 1. List-page pattern
- **MudDataGrid** med server-side paging (default 25 rækker)
- **MudTextField** søgefelt øverst til venstre
- **MudButton** "Opret ny" øverst til højre (kun hvis POST er tilgængeligt)
- Klik på række → åbner detalje-dialog (MudDialog)
- Slet via **MudIconButton** (skraldespand) + bekræftelsesdialog

### 2. Create/Edit dialog pattern
- **MudDialog** i stedet for separate sider
- **MudForm** med **MudTextField**, **MudSelect**, **MudDatePicker** efter behov
- Knapper: "Gem" (primary) og "Annuller" (secondary)
- Validering: FluentValidation-fejl vises inline

### 3. Confirm-delete pattern
- **MudDialog**: "Er du sikker på du vil slette [navn]?"
- Knapper: "Slet" (error color) og "Annuller"
- Efter slet: grid refresh + MudSnackbar "Slettet"

### 4. Navigation
- **MudNavMenu** i venstre sidebar
- Gruperet per domæne med **MudNavGroup** (collapsible)
- Aktiv side markeret med highlight
- Mobile: **MudDrawer** swipe-in

### 5. Feedback pattern
- Success: **MudSnackbar** grøn, 3 sek
- Error: **MudSnackbar** rød, persistent
- Loading: **MudProgressLinear** øverst på siden (ikke spinner)

### 6. Empty state pattern
- Ingen data: **MudAlert** Severity="Info" med opfordringstekst
- "Ingen [ressource] fundet. Opret den første!"

### 7. Auth/Adgang
- Sider kræver **[Authorize]** attribute
- Admin-sider kræver **[Authorize(Roles = "Admin")]**
- UI-elementer der kræver rettigheder: AuthorizeView + Policies
"""

TECH_STACK = """
## Tech Stack (LÅST — må ikke ændres)

| Lag | Teknologi |
|-----|-----------|
| Runtime | .NET 10 / C# 13 |
| Arkitektur | Vertical Slice (feature-mappe) |
| Frontend | Blazor Server + MudBlazor 8 |
| Data | Dapper + Z.Dapper.Plus |
| Auth | Custom JWT — ICurrentUser |
| Mediator | MediatR + FluentValidation |
| Tests | xUnit v3 + NSubstitute |
| CSS | design-tokens.css → SSOT |
| Icons | Material Icons via MudBlazor |
"""

BUILD_RULES = """
## AI Build Regler (ALLE AI-agenter følger disse)

1. **Ét vertical slice per user story** — feature-mappe med Query/Command/Handler/Endpoint
2. **Ingen EF Core** — kun Dapper SQL
3. **Ingen CSS overrides** — brug kun design-tokens.css vars
4. **Ingen inline styles** — brug `.ga-*` utility classes fra portal-skin.css
5. **Tests altid med** — xUnit + NSubstitute, named: `Method_State_Expected`
6. **Labels fra lokalisering** — `ILabelService.Get("KEY")` — ingen hardcoded tekst
7. **Navigation tilføjes** automatisk til `NavMenu.razor` under korrekt domæne-gruppe
8. **MudBlazor components** — se Shared Patterns ovenfor
9. **ICurrentUser** for auth-context — ingen HttpContext direkte
10. **ActivityLog** — alle COMMAND-operationer logger via `IActivityLogService`

## Vedligeholdelse (fremtidig AI)
- Hvert slice er selvstændigt — ændringer påvirker ikke andre slices
- Tilføj ny story: kør `get_story_context.py --story "X"` → får fuld implementeringskontekst
- Opdater harvest: kør `smart_harvester.py --all --overwrite` → genkør pipeline
- UI manifest opdateres automatisk ved ny story via denne pipeline
"""

# ──────────────────────────────────────────────────────────────────
# PAGE STRUCTURE
# ──────────────────────────────────────────────────────────────────
def build_page(story: dict) -> dict:
    """Byg side-definition fra user story."""
    verbs = story.get("verbs", [])
    resource = story.get("resource", "")
    resource_da = story.get("resource_da", resource)
    blazor = story.get("blazor", {})

    features = []
    if "GET" in verbs:
        features += ["list", "search", "filter"]
    if "POST" in verbs:
        features.append("create")
    if "PUT" in verbs or "PATCH" in verbs:
        features.append("edit")
    if "DELETE" in verbs:
        features.append("delete")

    return {
        "story_id": story["id"],
        "capability": story["capability"],
        "label_da": f"{resource_da.capitalize()}",
        "route": blazor.get("route", f"/{resource}"),
        "blazor_page": blazor.get("page", ""),
        "features": features,
        "components": blazor.get("components", []),
        "patterns": blazor.get("patterns", []),
        "priority": story["priority"],
        "story_da": story["story_da"],
        "acceptance_criteria": story.get("acceptance_criteria", []),
    }


def build_nav_structure(stories_by_domain: dict) -> list:
    """Byg navigationsstruktur fra alle domæner."""
    nav = []
    for domain_name, stories in stories_by_domain:
        pages = []
        for s in sorted(stories, key=lambda x: x["priority"]):
            blazor = s.get("blazor", {})
            pages.append({
                "story_id": s["id"],
                "label_da": s["resource_da"].capitalize(),
                "route": blazor.get("route", ""),
                "icon": None,
                "priority": s["priority"],
            })

        dom_cfg_nav = stories[0]["nav"] if stories else {}
        nav.append({
            "domain": domain_name,
            "label_da": dom_cfg_nav.get("domain_label", domain_name),
            "route_prefix": dom_cfg_nav.get("domain_route", ""),
            "icon": dom_cfg_nav.get("icon", "Help"),
            "nav_order": dom_cfg_nav.get("nav_order", 99),
            "pages": pages,
        })
    return nav


# ──────────────────────────────────────────────────────────────────
# MARKDOWN BUILDERS
# ──────────────────────────────────────────────────────────────────
def build_masterplan_md(data: dict, stories_by_domain: dict) -> str:
    lines = []
    meta = data["meta"]

    lines.append("# ServiceAlert → GreenAI — UI Masterplan\n\n")
    lines.append(f"**Genereret:** {meta['generated_at']}  \n")
    lines.append(f"**Kilde:** {meta['total_behaviors_english']} engelske behaviors + {meta['total_behaviors_danish']} danske behaviors  \n")
    lines.append(f"**User stories:** {meta['total_stories']}  \n")
    lines.append(f"**Domæner:** {meta['total_domains']}  \n\n")
    lines.append("---\n\n")

    lines.append("## Vision\n\n")
    lines.append("ServiceAlert UI er et professionelt enterprise-dashboard bygget i **Blazor Server + MudBlazor 8**.\n")
    lines.append("Systemet håndterer bulk-notifikationer (SMS, web-beskeder) til tusindvis af modtagere via et struktureret\n")
    lines.append("admin-interface. Alle sider følger ét konsistent design-sprog med venstre navigation, data-grid layouts\n")
    lines.append("og modal-dialoger for CRUD-operationer.\n\n")
    lines.append("**Rød tråd:** Desktop-first, data-tæt, keyboard-navigerbar, hurtige svar (<200ms), ingen page reloads.\n\n")
    lines.append("---\n\n")

    lines.append(TECH_STACK)
    lines.append("\n---\n\n")
    lines.append(SHARED_PATTERNS)
    lines.append("\n---\n\n")
    lines.append(BUILD_RULES)
    lines.append("\n---\n\n")

    # Navigation overview
    lines.append("## Navigationsstruktur\n\n")
    lines.append("```\nApp\n├── Dashboard (/)          ← overblik, KPI-widgets\n")
    for dom_name, stories in stories_by_domain:
        dom_nav = stories[0]["nav"] if stories else {}
        route = dom_nav.get("domain_route", "")
        label = dom_nav.get("domain_label", dom_name)
        lines.append(f"├── {label} ({route})\n")
        for s in sorted(stories[:6], key=lambda x: x["priority"]):  # max 6 per domain
            page_route = s["blazor"].get("route", "")
            res = s["resource_da"].capitalize()
            lines.append(f"│   ├── {res} ({page_route})\n")
        if len(stories) > 6:
            lines.append(f"│   └── ... +{len(stories)-6} mere\n")
    lines.append("└── Indstillinger (/settings)\n```\n\n")
    lines.append("---\n\n")

    # Per domain deep dive
    lines.append("## Sider per domæne\n\n")
    for dom_name, stories in stories_by_domain:
        dom_nav = stories[0]["nav"] if stories else {}
        label = dom_nav.get("domain_label", dom_name)
        route = dom_nav.get("domain_route", "")
        icon = dom_nav.get("icon", "")

        lines.append(f"### {label} `{route}` (icon: {icon})\n\n")

        p1 = [s for s in stories if s["priority"] == "P1"]
        p2 = [s for s in stories if s["priority"] == "P2"]
        p3 = [s for s in stories if s["priority"] == "P3"]

        for priority_group, label_p in [(p1, "P1 — Kritisk"), (p2, "P2 — Vigtig"), (p3, "P3 — Nice-to-have")]:
            if not priority_group:
                continue
            lines.append(f"**{label_p}:**\n\n")
            for s in priority_group:
                blazor = s.get("blazor", {})
                lines.append(f"#### [{s['id']}] {s['capability']}\n")
                lines.append(f"- **Story:** {s['story_da']}\n")
                lines.append(f"- **Side:** `{blazor.get('page', '')}`\n")
                lines.append(f"- **Route:** `{blazor.get('route', '')}`\n")
                lines.append(f"- **Components:** {', '.join(blazor.get('components', []))}\n")
                lines.append("- **Acceptkriterier:**\n")
                for ac in s.get("acceptance_criteria", []):
                    lines.append(f"  - {ac}\n")
                if s.get("source_behaviors"):
                    lines.append("- **Behaviors fra sms-service:**\n")
                    for b in s["source_behaviors"][:4]:
                        actor_da = "Bruger" if b["actor"] == "user" else "System"
                        lines.append(f"  - [{b['classification']}] {actor_da}: {b['text']}\n")
                lines.append("\n")

    return "".join(lines)


def build_prompt_pack_md(data: dict, stories_by_domain: dict) -> str:
    """Mega-prompt til den LLM der skal bygge hele UI'et."""
    meta = data["meta"]
    lines = []

    lines.append("# PROMPT PACK — AI Build Instruction for ServiceAlert GreenAI UI\n\n")
    lines.append("## Instruktioner til AI-agenten\n\n")
    lines.append("Du er en expert Blazor Server + MudBlazor 8 UI-builder. Du skal bygge et komplet enterprise UI\n")
    lines.append(f"baseret på {meta['total_stories']} user stories fra ServiceAlert.\n\n")
    lines.append("**Tech stack:** .NET 10, C# 13, Blazor Server, MudBlazor 8, Dapper, MediatR, xUnit v3\n\n")
    lines.append("**Vigtigste regel:** Ét vertical slice per user story. Hvert slice er selvstændigt og testbart.\n\n")
    lines.append("---\n\n")

    lines.append("## Build-sekvens (prioriteret)\n\n")
    lines.append("Byg i denne rækkefølge:\n\n")

    all_stories = data["user_stories"]
    for priority in ["P1", "P2", "P3"]:
        p_stories = [s for s in all_stories if s["priority"] == priority]
        if not p_stories:
            continue
        lines.append(f"### {priority} ({len(p_stories)} stories)\n\n")
        for s in p_stories:
            lines.append(f"- **{s['id']}** — {s['capability']} ({s['domain']})\n")
            lines.append(f"  - Story: {s['story_da']}\n")
            lines.append(f"  - Side: `{s['blazor']['page']}`\n")
            lines.append(f"  - Verbs: {', '.join(s['verbs'])}\n")
        lines.append("\n")

    lines.append("---\n\n")
    lines.append("## Shared Components (byg FØRST)\n\n")
    lines.append("Inden du bygger individuelle sider, byg disse delte komponenter:\n\n")
    lines.append("1. `Shared/DataGrid/AppDataGrid.razor` — wraps MudDataGrid med standard search + paging\n")
    lines.append("2. `Shared/Dialogs/ConfirmDeleteDialog.razor` — standardiseret sletbekræftelse\n")
    lines.append("3. `Shared/Dialogs/BaseFormDialog.razor` — standard create/edit dialog ramme\n")
    lines.append("4. `Shared/Feedback/AppSnackbar.razor` — centraliseret feedback service\n")
    lines.append("5. `Layout/NavMenu.razor` — auto-genereret fra nav-manifest\n\n")
    lines.append("---\n\n")

    lines.append("## User Stories (fuld liste)\n\n")
    for s in all_stories:
        lines.append(f"### {s['id']} — {s['capability']} [{s['priority']}]\n\n")
        lines.append(f"**Domæne:** {s['domain_da']}  \n")
        lines.append(f"**Story:** {s['story_da']}  \n")
        lines.append(f"**Verbs:** {', '.join(s['verbs'])}  \n")
        lines.append(f"**Ressource:** {s['resource_da']}  \n\n")
        lines.append("**Acceptkriterier:**\n")
        for ac in s["acceptance_criteria"]:
            lines.append(f"- {ac}\n")
        lines.append(f"\n**Blazor side:** `{s['blazor']['page']}`  \n")
        lines.append(f"**Route:** `{s['blazor']['route']}`  \n")
        lines.append(f"**MudBlazor:** {', '.join(s['blazor']['components'])}  \n")
        lines.append(f"**Patterns:** {', '.join(s['blazor']['patterns'])}  \n\n")
        if s.get("source_behaviors"):
            lines.append("**Context fra sms-service (implementeringsinspirasjon):**\n")
            for b in s["source_behaviors"][:6]:
                actor_da = "Bruger" if b["actor"] == "user" else "System"
                lines.append(f"- {actor_da}: {b['text']}\n")
        lines.append("\n---\n\n")

    return "".join(lines)


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate Blazor UI masterplan from user stories")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not USER_STORIES_PATH.exists():
        print(f"FEJL: {USER_STORIES_PATH} ikke fundet. Kør generate_user_stories.py først.")
        return 1

    data = json.loads(USER_STORIES_PATH.read_text(encoding="utf-8"))
    all_stories = data["user_stories"]

    # Group by domain (preserving nav_order sort)
    domain_order = {d["name"]: d.get("nav_order", 99) for d in data.get("domains", [])}
    raw_by_domain: dict[str, list] = defaultdict(list)
    for s in all_stories:
        raw_by_domain[s["domain"]].append(s)

    stories_by_domain = sorted(
        raw_by_domain.items(),
        key=lambda x: domain_order.get(x[0], 99),
    )

    print(f"Loaded {len(all_stories)} user stories across {len(stories_by_domain)} domains")

    # Build manifest
    pages_by_domain = {}
    for dom_name, stories in stories_by_domain:
        pages_by_domain[dom_name] = [build_page(s) for s in sorted(stories, key=lambda x: x["priority"])]

    nav = build_nav_structure(stories_by_domain)

    manifest = {
        "meta": {
            "generated_at": data["meta"]["generated_at"],
            "total_stories": len(all_stories),
            "total_pages": sum(len(p) for p in pages_by_domain.values()),
            "total_domains": len(stories_by_domain),
        },
        "navigation": nav,
        "pages_by_domain": pages_by_domain,
        "shared_components": [
            {
                "name": "AppDataGrid",
                "path": "Shared/DataGrid/AppDataGrid.razor",
                "wraps": "MudDataGrid",
                "purpose": "Standard list-view med søgning og paging",
            },
            {
                "name": "ConfirmDeleteDialog",
                "path": "Shared/Dialogs/ConfirmDeleteDialog.razor",
                "wraps": "MudDialog",
                "purpose": "Standardiseret sletbekræftelse",
            },
            {
                "name": "BaseFormDialog",
                "path": "Shared/Dialogs/BaseFormDialog.razor",
                "wraps": "MudDialog + MudForm",
                "purpose": "Opret/redigér dialog ramme",
            },
            {
                "name": "AppSnackbar",
                "path": "Shared/Feedback/AppSnackbar.razor",
                "wraps": "MudSnackbar",
                "purpose": "Centraliseret success/error feedback",
            },
        ],
    }

    p1_count = sum(1 for s in all_stories if s["priority"] == "P1")
    p2_count = sum(1 for s in all_stories if s["priority"] == "P2")
    p3_count = sum(1 for s in all_stories if s["priority"] == "P3")
    print(f"\nUI Manifest: {manifest['meta']['total_pages']} sider, P1:{p1_count} P2:{p2_count} P3:{p3_count}")
    print(f"{len(nav)} domæner i navigation:")
    for n in nav:
        print(f"  {n['label_da']} ({n['route_prefix']}): {len(n['pages'])} sider")

    if args.dry_run:
        print("\n[DRY RUN] Ingen filer skrevet.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest_path = OUT_DIR / "ui_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Skrevet: {manifest_path} ({manifest_path.stat().st_size // 1024} KB)")

    # Write masterplan
    masterplan_md = build_masterplan_md(data, stories_by_domain)
    masterplan_path = OUT_DIR / "ui_masterplan.md"
    masterplan_path.write_text(masterplan_md, encoding="utf-8")
    print(f"✓ Skrevet: {masterplan_path} ({masterplan_path.stat().st_size // 1024} KB)")

    # Write prompt pack
    prompt_md = build_prompt_pack_md(data, stories_by_domain)
    prompt_path = OUT_DIR / "story_prompt_pack.md"
    prompt_path.write_text(prompt_md, encoding="utf-8")
    print(f"✓ Skrevet: {prompt_path} ({prompt_path.stat().st_size // 1024} KB)")

    print("\nFærdig! Næste: send ui_masterplan.md til arkitekten for godkendelse.")
    return 0


if __name__ == "__main__":
    main()
