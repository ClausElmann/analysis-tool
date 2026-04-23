#!/usr/bin/env python3
"""
generate_user_stories.py — Kombiner gammel + ny harvest → strukturerede Blazor user stories

Læser:
  harvest/angularharvest/capabilities_grouped.json  (48 capability groups)
  harvest/angularharvest/behaviors_verified.json    (630 VERIFIED behaviors)
  harvest/angularharvest/behaviors_inferred.json    (89 INFERRED behaviors)
  harvest/angularharvest/domains_grouped.json       (6 domæner)
  harvest/angular/raw/*/llm_output_validated.json   (593 danske komponent-behaviors)

Skriver:
  harvest/unified/user_stories.json                 (strukturerede user stories per capability)
  harvest/unified/user_stories_by_domain.md         (human-readable resumé)
  harvest/unified/behavior_pool.json                (alle behaviors samlet + deduplikeret)

Usage:
  python scripts/harvest/generate_user_stories.py
  python scripts/harvest/generate_user_stories.py --dry-run
"""

import argparse
import json
import re
import uuid
from pathlib import Path
from collections import defaultdict

HARVEST_DIR = Path("harvest/angularharvest")
RAW_DIR = Path("harvest/angular/raw")
OUT_DIR = Path("harvest/unified")

# ──────────────────────────────────────────────────────────────────
# DOMAIN CONFIG
# ──────────────────────────────────────────────────────────────────
DOMAIN_CONFIG = {
    "Messaging & Communication": {
        "label_da": "Beskeder & Kommunikation",
        "route": "/messaging",
        "icon": "Message",
        "nav_order": 1,
        "description_da": "Oprettelse, afsendelse og administration af beskeder, SMS, web-beskeder og broadcast-kanaler.",
    },
    "Customer & Enrollment": {
        "label_da": "Kunder & Tilmelding",
        "route": "/customers",
        "icon": "People",
        "nav_order": 2,
        "description_da": "Kundeadministration, afsender-tilmelding, kontakter og afmeldingsprocesser.",
    },
    "User & Access Management": {
        "label_da": "Brugere & Adgang",
        "route": "/admin",
        "icon": "AdminPanelSettings",
        "nav_order": 3,
        "description_da": "Brugerprofiler, roller, adgangsnøgler, pakker og applikationsindstillinger.",
    },
    "Address & Data": {
        "label_da": "Adresser & Data",
        "route": "/addresses",
        "icon": "LocationOn",
        "nav_order": 4,
        "description_da": "Adresseopslagning, geodata, modtagergrupper, filhåndtering og dataimport.",
    },
    "Finance & Operations": {
        "label_da": "Økonomi & Drift",
        "route": "/finance",
        "icon": "AccountBalance",
        "nav_order": 5,
        "description_da": "Fakturering, accruals, HR-fravær, lønsedler og driftsprocesser.",
    },
    "Analytics & Reporting": {
        "label_da": "Analyse & Rapportering",
        "route": "/analytics",
        "icon": "Analytics",
        "nav_order": 6,
        "description_da": "Benchmark-statistik, KPI-opfølgning, årsagskoder og audit-log.",
    },
}

# ──────────────────────────────────────────────────────────────────
# RESOURCE → DANSK
# ──────────────────────────────────────────────────────────────────
RESOURCE_DA = {
    "message": "beskeder",
    "customer": "kunder",
    "user": "brugere",
    "profile": "profiler",
    "sender": "afsendere",
    "address": "adresser",
    "invoice": "fakturaer",
    "report": "rapporter",
    "enrollment": "tilmeldinger",
    "group": "grupper",
    "role": "roller",
    "contact": "kontakter",
    "conversation": "samtaler",
    "benchmark": "benchmarks",
    "receiver": "modtagere",
    "map": "kortvisning",
    "web": "web-beskeder",
    "sms": "SMS-beskeder",
    "import": "dataimport",
    "salary": "lønsedler",
    "absence": "fraværsregistreringer",
    "warning": "advarsler",
    "weather": "vejrdata",
    "drive": "fildrev",
    "archived": "arkiverede beskeder",
    "configuration": "konfigurationer",
    "status": "statusoversigt",
    "ftp": "FTP-filer",
    "entry": "poster",
    "std": "standardindstillinger",
    "localized": "sprogoversættelser",
    "employee": "medarbejdere",
    "correction": "korrektioner",
    "cause": "årsagskoder",
    "operational": "driftsdata",
    "prospect": "salgsmuligheder",
    "sale": "salgsdata",
    "reset": "nulstillinger",
    "dynamic": "dynamiske felter",
    "gdpr": "GDPR-håndtering",
    "statsstidende": "statsstidende-opslag",
}

# ──────────────────────────────────────────────────────────────────
# VERB → AKSIONER
# ──────────────────────────────────────────────────────────────────
VERB_ACTION_DA = {
    "GET":    "se og søge i",
    "POST":   "oprette",
    "PUT":    "redigere",
    "PATCH":  "opdatere",
    "DELETE": "slette",
}

DOMAIN_VALUE = {
    "Messaging & Communication": "kommunikere effektivt med kunder og modtagere",
    "Customer & Enrollment":     "administrere kundernes tilmeldingsforhold og kontaktdata",
    "User & Access Management":  "styre brugeradgang og sikkerhed i systemet",
    "Address & Data":            "håndtere og validere adressedata korrekt",
    "Finance & Operations":      "holde styr på økonomi og driftsprocesser",
    "Analytics & Reporting":     "få indsigt i systemaktivitet og performance",
}

# ──────────────────────────────────────────────────────────────────
# MUDBLAZOR HINTS
# ──────────────────────────────────────────────────────────────────
def get_mudblazor_hints(verbs: list, resource: str) -> dict:
    components = []
    patterns = []

    if "GET" in verbs:
        components += ["MudDataGrid", "MudTextField"]
        patterns += ["list-with-search", "pagination"]
    if "POST" in verbs:
        components += ["MudButton", "MudDialog", "MudForm"]
        patterns += ["create-dialog"]
    if "PUT" in verbs or "PATCH" in verbs:
        components += ["MudIconButton", "MudDialog", "MudForm"]
        patterns += ["edit-dialog"]
    if "DELETE" in verbs:
        components += ["MudIconButton", "MudDialog"]
        patterns += ["confirm-delete-dialog"]

    # Resource-specifikke hints
    if resource in ("map", "address"):
        components.append("MudPaper")  # kort container
        patterns.append("map-view")
    if resource in ("benchmark", "report"):
        components += ["MudChart", "MudCard"]
        patterns.append("stats-cards")

    return {
        "components": sorted(set(components)),
        "patterns": sorted(set(patterns)),
    }


def get_acceptance_criteria(verbs: list, resource_da: str) -> list:
    ac = []
    if "GET" in verbs:
        ac.append(f"Brugeren ser en liste over {resource_da}")
        ac.append(f"Brugeren kan søge og filtrere {resource_da}")
    if "POST" in verbs:
        ac.append(f"Brugeren kan oprette ny/nye {resource_da} via formular")
    if "PUT" in verbs or "PATCH" in verbs:
        ac.append(f"Brugeren kan redigere eksisterende {resource_da}")
    if "DELETE" in verbs:
        ac.append(f"Brugeren kan slette {resource_da} med bekræftelsesdialog")
    return ac


def get_story_verb_da(verbs: list, resource_da: str) -> str:
    parts = []
    if "GET" in verbs:
        parts.append(f"se og søge i {resource_da}")
    if "POST" in verbs:
        parts.append(f"oprette {resource_da}")
    if "PUT" in verbs or "PATCH" in verbs:
        parts.append(f"redigere {resource_da}")
    if "DELETE" in verbs:
        parts.append(f"slette {resource_da}")
    if not parts:
        return f"arbejde med {resource_da}"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f" og {parts[-1]}"


def capability_to_page_name(cap_name: str) -> str:
    """'Manage Messages' → 'MessagesPage'"""
    parts = cap_name.split()
    if parts[0].lower() in ("manage", "other"):
        entity = "".join(w.capitalize() for w in parts[1:])
        return f"{entity}Page"
    return "".join(w.capitalize() for w in parts) + "Page"


def get_priority(domain: str, verbs: list) -> str:
    high_domains = {"Messaging & Communication", "Customer & Enrollment"}
    if domain in high_domains and "POST" in verbs:
        return "P1"
    if domain in high_domains:
        return "P2"
    return "P3"


# ──────────────────────────────────────────────────────────────────
# LOAD NEW HARVEST (danske komponent-behaviors)
# ──────────────────────────────────────────────────────────────────
def load_new_harvest_behaviors() -> dict[str, list[str]]:
    """Returnerer dict: komponent_navn → [dansk behavior tekst]"""
    result = {}
    if not RAW_DIR.exists():
        return result
    for component_dir in RAW_DIR.iterdir():
        validated = component_dir / "llm_output_validated.json"
        if not validated.exists():
            continue
        try:
            data = json.loads(validated.read_text(encoding="utf-8"))
            behaviors = [
                b["text"]
                for b in data.get("behaviors", [])
                if b.get("status") == "PASS" and b.get("text")
            ]
            if behaviors:
                result[component_dir.name] = behaviors
        except Exception:
            pass
    return result


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate Blazor user stories from harvest")
    parser.add_argument("--dry-run", action="store_true", help="Print output, do not write files")
    args = parser.parse_args()

    # Load old harvest
    caps_data = json.loads((HARVEST_DIR / "capabilities_grouped.json").read_text(encoding="utf-8"))
    bv_data = json.loads((HARVEST_DIR / "behaviors_verified.json").read_text(encoding="utf-8"))
    bi_data = json.loads((HARVEST_DIR / "behaviors_inferred.json").read_text(encoding="utf-8"))
    domains_data = json.loads((HARVEST_DIR / "domains_grouped.json").read_text(encoding="utf-8"))

    capabilities = caps_data["capabilities_grouped"]
    behaviors_verified = bv_data["behaviors"]
    behaviors_inferred = bi_data["behaviors"]
    domains = domains_data["domains_grouped"]

    # Index behaviors by source_capability_ids for enrichment
    cap_to_behaviors: dict[str, list] = defaultdict(list)
    for b in behaviors_verified:
        for cap_id in b.get("source_capability_ids", []):
            cap_to_behaviors[cap_id].append(b)
    for b in behaviors_inferred:
        for cap_id in b.get("source_capability_ids", []):
            cap_to_behaviors[cap_id].append(b)

    # Load new harvest (danish)
    new_behaviors = load_new_harvest_behaviors()
    print(f"Loaded {len(new_behaviors)} components with Danish behaviors from new harvest")

    # Build behavior pool (all combined)
    behavior_pool = {
        "verified_count": len(behaviors_verified),
        "inferred_count": len(behaviors_inferred),
        "danish_component_count": len(new_behaviors),
        "danish_behavior_count": sum(len(v) for v in new_behaviors.values()),
        "verified": behaviors_verified,
        "inferred": behaviors_inferred,
        "danish_by_component": new_behaviors,
    }

    # Build domain index
    domain_index = {d["name"]: d for d in domains}

    # Generate user stories
    user_stories = []
    stories_by_domain: dict[str, list] = defaultdict(list)
    story_counter = 1

    for cap in capabilities:
        cap_name = cap["name"]
        domain_name = cap.get("domain", "Unknown")
        resource = cap.get("resource", "").lower()
        verbs = cap.get("verbs", ["GET"])
        cap_ids = cap.get("source_capability_ids", [])

        # Resolve Danish resource label
        resource_da = RESOURCE_DA.get(resource, resource + "er")

        # Domain config
        dom_cfg = DOMAIN_CONFIG.get(domain_name, {
            "label_da": domain_name,
            "route": "/misc",
            "icon": "Help",
            "nav_order": 99,
        })

        # Story verb phrase
        verb_phrase = get_story_verb_da(verbs, resource_da)
        value = DOMAIN_VALUE.get(domain_name, f"arbejde effektivt med {resource_da}")

        # Acceptance criteria
        ac = get_acceptance_criteria(verbs, resource_da)

        # MudBlazor hints
        mud = get_mudblazor_hints(verbs, resource)

        # Blazor page path
        page_name = capability_to_page_name(cap_name)
        blazor_page = f"Pages{dom_cfg['route']}/{page_name}.razor"

        # Related old behaviors (English context)
        related_behaviors = []
        for cid in cap_ids:
            for b in cap_to_behaviors.get(cid, []):
                related_behaviors.append({
                    "text": b["text"],
                    "actor": b.get("actor", "user"),
                    "classification": b.get("classification", "VERIFIED"),
                })
        # Deduplicate
        seen_texts = set()
        unique_behaviors = []
        for b in related_behaviors:
            if b["text"] not in seen_texts:
                seen_texts.add(b["text"])
                unique_behaviors.append(b)

        story_id = f"US-{story_counter:03d}"
        story_counter += 1

        story = {
            "id": story_id,
            "domain": domain_name,
            "domain_da": dom_cfg["label_da"],
            "capability": cap_name,
            "resource": resource,
            "resource_da": resource_da,
            "verbs": verbs,
            "priority": get_priority(domain_name, verbs),
            "story_da": f"Som bruger vil jeg {verb_phrase}, så jeg kan {value}.",
            "acceptance_criteria": ac,
            "blazor": {
                "page": blazor_page,
                "route": f"{dom_cfg['route']}/{resource}s",
                **mud,
            },
            "nav": {
                "domain_label": dom_cfg["label_da"],
                "domain_route": dom_cfg["route"],
                "icon": dom_cfg["icon"],
                "nav_order": dom_cfg["nav_order"],
            },
            "source_behaviors": unique_behaviors[:10],  # max 10 for brevity
            "source_capability_ids": cap_ids,
        }

        user_stories.append(story)
        stories_by_domain[domain_name].append(story)

    print(f"\nGenereret {len(user_stories)} user stories på tværs af {len(stories_by_domain)} domæner")
    for dom, stories in sorted(stories_by_domain.items(), key=lambda x: DOMAIN_CONFIG.get(x[0], {}).get("nav_order", 99)):
        p1 = sum(1 for s in stories if s["priority"] == "P1")
        p2 = sum(1 for s in stories if s["priority"] == "P2")
        p3 = sum(1 for s in stories if s["priority"] == "P3")
        print(f"  {dom}: {len(stories)} stories (P1:{p1} P2:{p2} P3:{p3})")

    if args.dry_run:
        print("\n[DRY RUN] Ingen filer skrevet.")
        print("\nSample story:")
        print(json.dumps(user_stories[0], ensure_ascii=False, indent=2))
        return

    # Write output
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "meta": {
            "generated_at": "2026-04-23",
            "source": "angular_harvest_v3 + smart_harvester_v1",
            "total_stories": len(user_stories),
            "total_domains": len(stories_by_domain),
            "total_behaviors_english": len(behaviors_verified) + len(behaviors_inferred),
            "total_behaviors_danish": sum(len(v) for v in new_behaviors.values()),
        },
        "domains": [
            {
                "name": dom,
                **DOMAIN_CONFIG.get(dom, {}),
                "story_count": len(stories),
            }
            for dom, stories in sorted(
                stories_by_domain.items(),
                key=lambda x: DOMAIN_CONFIG.get(x[0], {}).get("nav_order", 99),
            )
        ],
        "user_stories": user_stories,
    }

    out_json = OUT_DIR / "user_stories.json"
    out_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Skrevet: {out_json} ({out_json.stat().st_size // 1024} KB)")

    # Write behavior pool
    pool_path = OUT_DIR / "behavior_pool.json"
    pool_path.write_text(json.dumps(behavior_pool, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Skrevet: {pool_path} ({pool_path.stat().st_size // 1024} KB)")

    # Write markdown summary
    md_lines = ["# User Stories — ServiceAlert → GreenAI\n"]
    md_lines.append(f"**Genereret:** 2026-04-23  \n**Kilde:** {len(behaviors_verified)} verified + {len(behaviors_inferred)} inferred behaviors + {sum(len(v) for v in new_behaviors.values())} danske komponent-behaviors  \n**Total:** {len(user_stories)} user stories\n\n---\n")

    for dom_name, stories in sorted(
        stories_by_domain.items(),
        key=lambda x: DOMAIN_CONFIG.get(x[0], {}).get("nav_order", 99),
    ):
        dom_cfg = DOMAIN_CONFIG.get(dom_name, {})
        md_lines.append(f"\n## {dom_cfg.get('label_da', dom_name)}\n")
        md_lines.append(f"*{dom_name}*  \n{domain_index.get(dom_name, {}).get('description_da', '')}  \nRoute: `{dom_cfg.get('route', '')}`\n")

        for s in sorted(stories, key=lambda x: x["priority"]):
            md_lines.append(f"\n### [{s['id']}] {s['capability']} `{s['priority']}`\n")
            md_lines.append(f"**Story:** {s['story_da']}\n")
            md_lines.append("**Acceptkriterier:**\n")
            for ac in s["acceptance_criteria"]:
                md_lines.append(f"- {ac}\n")
            md_lines.append(f"\n**Blazor:** `{s['blazor']['page']}`  \n")
            md_lines.append(f"**MudBlazor:** {', '.join(s['blazor']['components'])}  \n")
            md_lines.append(f"**Patterns:** {', '.join(s['blazor']['patterns'])}  \n")
            if s["source_behaviors"]:
                md_lines.append("\n**Behaviors fra høst:**\n")
                for b in s["source_behaviors"][:5]:
                    actor_da = "Bruger" if b["actor"] == "user" else "System"
                    md_lines.append(f"- [{b['classification']}] {actor_da}: {b['text']}\n")

    out_md = OUT_DIR / "user_stories_by_domain.md"
    out_md.write_text("".join(md_lines), encoding="utf-8")
    print(f"✓ Skrevet: {out_md} ({out_md.stat().st_size // 1024} KB)")
    print("\nFærdig!")


if __name__ == "__main__":
    main()
