"""
SMART Component Behavior Harvester v1

Genererer llm_output.json for SMART/CONTAINER komponenter fra evidence_pack.json.
Ingen LLM påkrævet — bruger struktureret mapping fra HTTP-verb + metodenavn.

Formål (Tier 1):
  Producere korte, bruger-vendte behaviors til user story-planlægning i GreenAI.
  Eksempel output: "Brugeren kan søge i arkiverede beskeder for adresse"

Pipeline-placering:
  build_evidence_packs.py → [denne fil] → validate_llm_output.py → emit_to_jsonl.py

Usage:
    python scripts/harvest/smart_harvester.py --all
    python scripts/harvest/smart_harvester.py --component bi-address-search
    python scripts/harvest/smart_harvester.py --all --dry-run
    python scripts/harvest/smart_harvester.py --all --overwrite
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Argument parsing ───────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Generate llm_output.json for SMART components")
parser.add_argument("--component",      default=None,    help="Single component name to process")
parser.add_argument("--component-list", default=r".\harvest\component-list.json")
parser.add_argument("--raw-dir",        default=r".\harvest\angular\raw")
parser.add_argument("--all",            action="store_true", help="Process all SMART components found in raw-dir")
parser.add_argument("--dry-run",        action="store_true", help="Print output, don't write files")
parser.add_argument("--overwrite",      action="store_true", help="Overwrite existing llm_output.json")
args = parser.parse_args()

RAW_DIR = Path(args.raw_dir)

# ── Verb → Danish action ───────────────────────────────────────────────────────
VERB_DA: dict[str, str] = {
    "get":         "se",
    "getall":      "se alle",
    "load":        "se",
    "list":        "se liste over",
    "fetch":       "hente",
    "retrieve":    "hente",
    "download":    "downloade",
    "export":      "eksportere",
    "search":      "søge efter",
    "find":        "finde",
    "lookup":      "slå op",
    "create":      "oprette",
    "add":         "tilføje",
    "insert":      "tilføje",
    "update":      "opdatere",
    "edit":        "redigere",
    "save":        "gemme",
    "put":         "opdatere",
    "patch":       "opdatere",
    "set":         "ændre",
    "toggle":      "skifte",
    "delete":      "slette",
    "remove":      "fjerne",
    "upload":      "uploade",
    "import":      "importere",
    "send":        "sende",
    "finish":      "afslutte",
    "complete":    "gennemføre",
    "approve":     "godkende",
    "reject":      "afvise",
    "unsubscribe": "afmelde",
    "subscribe":   "tilmelde",
    "assign":      "tildele",
    "register":    "registrere",
    "confirm":     "bekræfte",
    "cancel":      "annullere",
    "reset":       "nulstille",
    "check":       "se status for",
    "validate":    "validere",
    "verify":      "verificere",
    "mark":        "markere",
    "archive":     "arkivere",
    "restore":     "gendanne",
    "copy":        "kopiere",
    "merge":       "flette",
    "generate":    "generere",
    "process":     "behandle",
    "open":        "åbne",
    "close":       "lukke",
    "start":       "starte",
    "stop":        "stoppe",
    "show":        "se",
    "view":        "se",
    "display":     "vise",
    "filter":      "filtrere",
    "sort":        "sortere",
    "select":      "vælge",
    "selected":    "vælge",
    "choose":      "vælge",
    "refresh":     "opdatere",
    "reload":      "genindlæse",
    "submit":      "indsende",
    "print":       "udskrive",
    "preview":     "forhåndsvise",
    "share":       "dele",
    "map":         "kortlægge",
    "resolve":     "løse",
}

# ── HTTP verb fallback ─────────────────────────────────────────────────────────
HTTP_VERB_DA: dict[str, str] = {
    "GET":    "se",
    "POST":   "oprette",
    "PUT":    "oprette",
    "PATCH":  "opdatere",
    "DELETE": "slette",
}

# ── Entity word translations (English → Danish) ────────────────────────────────
ENTITY_DA: dict[str, str] = {
    # Messages
    "message":        "besked",
    "messages":       "beskeder",
    "webmessage":     "web-besked",
    "webmessages":    "web-beskeder",
    "draft":          "kladde",
    "drafts":         "kladder",
    "template":       "skabelon",
    "templates":      "skabeloner",
    "broadcast":      "udsendelse",
    "broadcasts":     "udsendelser",
    "conversation":   "samtale",
    "conversations":  "samtaler",
    "sms":            "SMS",
    "email":          "email",
    "notification":   "notifikation",
    "notifications":  "notifikationer",
    "stencil":        "stencil",
    "newsletter":     "nyhedsbrev",
    # Address/Geo
    "address":        "adresse",
    "addresses":      "adresser",
    "street":         "gade",
    "streets":        "gader",
    "streetname":     "gadenavn",
    "streetnames":    "gadenavne",
    "zipcode":        "postnummer",
    "zip":            "postnummer",
    "municipality":   "kommune",
    "municipalities": "kommuner",
    "property":       "ejendom",
    "properties":     "ejendomme",
    "owner":          "ejer",
    "owners":         "ejere",
    "robinson":       "Robinson-registrering",
    "eboks":          "e-Boks",
    "contact":        "kontaktperson",
    "contacts":       "kontakter",
    "geo":            "geografisk",
    "map":            "kort",
    "coordinates":    "koordinater",
    # Users/Profiles
    "user":           "bruger",
    "users":          "brugere",
    "profile":        "profil",
    "profiles":       "profiler",
    "role":           "rolle",
    "roles":          "roller",
    "customer":       "kunde",
    "customers":      "kunder",
    "group":          "gruppe",
    "groups":         "grupper",
    "member":         "medlem",
    "members":        "medlemmer",
    "sender":         "afsender",
    "senders":        "afsendere",
    "receiver":       "modtager",
    "receivers":      "modtagere",
    "employee":       "medarbejder",
    "employees":      "medarbejdere",
    # Reports/Statistics
    "report":         "rapport",
    "reports":        "rapporter",
    "usage":          "forbrug",
    "statistic":      "statistik",
    "statistics":     "statistikker",
    "invoicing":      "fakturering",
    "invoice":        "faktura",
    "invoices":       "fakturaer",
    "accrual":        "periodisering",
    "salary":         "løn",
    "budget":         "budget",
    "kpi":            "KPI",
    "kpis":           "KPIer",
    # Benchmark
    "benchmark":      "benchmark",
    "benchmarks":     "benchmarks",
    "cause":          "årsagskode",
    "causes":         "årsagskoder",
    "category":       "kategori",
    "categories":     "kategorier",
    "supplytype":     "forsyningstype",
    "supplytypes":    "forsyningstyper",
    "smsgroup":       "SMS-gruppe",
    "smsgroups":      "SMS-grupper",
    "conflict":       "konflikt",
    # Social/Media
    "facebook":       "Facebook",
    "twitter":        "Twitter",
    "socialmedia":    "sociale medier",
    "social":         "sociale",
    "media":          "medier",
    # Phone/Subscription
    "phone":          "telefonnummer",
    "subscription":   "abonnement",
    "subscriptions":  "abonnementer",
    "enrollment":     "tilmelding",
    "enrollments":    "tilmeldinger",
    "operator":       "telefonoperatør",
    "company":        "virksomhed",
    "cvr":            "CVR-nummer",
    # Settings/Config
    "setting":        "indstilling",
    "settings":       "indstillinger",
    "configuration":  "konfiguration",
    "configurations": "konfigurationer",
    "apikey":         "API-nøgle",
    "apikeys":        "API-nøgler",
    "api":            "API",
    "key":            "nøgle",
    "keys":           "nøgler",
    # Files
    "file":           "fil",
    "files":          "filer",
    "image":          "billede",
    "images":         "billeder",
    "attachment":     "vedhæftet fil",
    "attachments":    "vedhæftede filer",
    # Common
    "status":         "status",
    "data":           "data",
    "access":         "adgang",
    "nudging":        "nudging",
    "right":          "ret",
    "forgotten":      "glemt",
    "archived":       "arkiverede",
    "country":        "land",
    "countries":      "lande",
    "count":          "antal",
    "detail":         "detalje",
    "details":        "detaljer",
    "date":           "dato",
    "task":           "opgave",
    "tasks":          "opgaver",
    "keyword":        "søgeord",
    "schedule":       "tidsplan",
    "scheduled":      "planlagt",
    "log":            "log",
    "logs":           "log-poster",
    "period":         "periode",
    "number":         "nummer",
    "numbers":        "numre",
    "type":           "type",
    "types":          "typer",
    "total":          "samlet",
    "summary":        "oversigt",
    "overview":       "oversigt",
    "item":           "element",
    "items":          "elementer",
    "list":           "liste",
    "index":          "oversigt",
    "prospect":       "emne",
    "prospects":      "emner",
    "product":        "produkt",
    "products":       "produkter",
    "invoice":        "faktura",
    "tag":            "tag",
    "tags":           "tags",
    "label":          "label",
    "labels":         "labels",
    "comment":        "kommentar",
    "comments":       "kommentarer",
    "note":           "note",
    "notes":          "noter",
    # Compound report/stat nouns (prevent "forbrug rapport" → "forbrugsrapport")
    "usagereport":         "forbrugsrapport",
    "usagereports":        "forbrugsrapporter",
    "invoicingreport":     "faktureringsrapport",
    "invoicingreports":    "faktureringsrapporter",
    "statisticreport":     "statistikrapport",
    "statisticsreport":    "statistikrapport",
    "messagereport":       "beskedrapport",
    "messagereports":      "beskedrapporter",
    "smsreport":           "SMS-rapport",
    "smsdetailsreport":    "detaljeret SMS-rapport",
    "draftreport":         "kladde-rapport",
    "draftsreport":        "kladde-rapport",
    "messagetemplate":     "besked-skabelon",
    "messagetemplates":    "besked-skabeloner",
    "usagecount":          "forbrugstal",
    "usagecounts":         "forbrugstal",
    "smsgroupsfor":        "SMS-grupper til",
}

# ── Words to skip in entity extraction ────────────────────────────────────────
ENTITY_SKIP: set[str] = {
    "sent", "to", "from", "by", "on", "at", "of", "for", "and", "or",
    "in", "per", "with", "the", "a", "an", "all", "new", "current",
    "day4day", "4", "using", "based", "related", "last", "recent",
    "latest", "active", "available", "get", "set", "is", "has", "can",
    "do", "cache", "cached", "state", "value",
    # UI/navigation words — no user-data meaning
    "msg", "page", "end", "click", "btn", "dialog", "modal",
    "item", "row", "col", "column", "cell", "panel", "tab", "section",
    "view", "area", "box", "card", "form",
}

# ── Click handler prefixes/suffixes to strip ───────────────────────────────────
HANDLER_STRIP_PREFIX = re.compile(r"^(on|handle|do)(?=[A-Z])", re.IGNORECASE)
HANDLER_STRIP_SUFFIX = re.compile(r"(Clicked|Click|Changed|Selected|Submitted|Pressed|Cliced|Triggered|Fired)$")

# ── Explicit overrides for click handlers (name → raw phrase or None=skip) ────
HANDLER_EXPLICIT: dict[str, str | None] = {
    "onStartOrEndClicked":  "åbne eller lukke web-besked",
    "onStartOrEnd":         "åbne eller lukke web-besked",
    "editConflict":         None,   # covered by getConflictingBenchmarks
    "resetPage":            None,   # pure UI reset, no user data action
    "selectedMessage":      "vælge besked",
    "onSmsGroupSelected":   "vælge SMS-gruppe",
    "onShowSmsGroupStatus":  "se SMS-gruppe status",
    "onFilterSmsGroups":    "filtrere SMS-grupper med dato",
    "getMessages":          "se beskeder i datointerval",
    "onAddNewMsgClicked":   "oprette ny web-besked",
    "loadInArchivedData":   "hente arkiverede data",
}

# ── Explicit behavior overrides (complex compound method names) ────────────────
# None = skip this method entirely
EXPLICIT: dict[str, str | None] = {
    # Address search — complex "sentTo" patterns
    "getMessagesSentToPhoneOrEmail":             "se beskeder sendt til telefonnummer eller email",
    "getArchivedMessagesSentToPhoneOrEmail":      "søge i arkiverede beskeder for telefonnummer",
    "downloadMessagesSentToPhoneOrEmail":         "downloade beskedhistorik for telefonnummer",
    "getMessagesSentToCompanyRegistrationId":     "se beskeder sendt til CVR-nummer",
    "getArchivedMessagesSentToCompanyRegistrationId": "søge i arkiverede beskeder for CVR-nummer",
    "downloadMessagesSentToCompanyRegistrationId": "downloade beskedhistorik for CVR-nummer",
    "getMessagesSentToPropertyId":               "se beskeder sendt til ejendom",
    "getArchivedMessagesSentToPropertyId":        "søge i arkiverede beskeder for ejendom",
    "getMessagesSentToAddress":                  "se beskeder sendt til adresse",
    "getArchivedMessagesSentToAddress":           "søge i arkiverede beskeder for adresse",
    # Address lookups with compound locations
    "getContactsByPropertyId":                   "se kontakter tilknyttet ejendom",
    "getContactsOnAddress":                      "se kontakter på adresse",
    "getOwnersOnAddress":                        "se ejere på adresse",
    "getOwnersByPropertyId":                     "se ejere af ejendom",
    "getPropertiesOwnedByPeopleOnAddress":        "se ejendomme ejet af beboere på adresse",
    "getRobinsonRegistrationsOnAddress":          "se Robinson-registreringer på adresse",
    # Statistics — compound names
    "getTotalUsageCountsDay4DayPerCountry":       "se dagligt forbrug per land",
    "getTotalUsageCounts":                        "se samlet forbrug for periode",
    "getPhoneOperatorAndSubscriptionsData":       "se telefonoperatør og abonnementsdata",
    # Status setters
    "setWebMessageClosedStatus":                 "åbne eller lukke web-besked",
    # Benchmark
    "getSmsGroupsForBenchmark":                  "tilknytte SMS-grupper til benchmark",
    "getSmsGroupsForBenchMark":                  "tilknytte SMS-grupper til benchmark",
    "getConflictingBenchmarks":                  "se overlappende benchmark-perioder",
    # Reports with complex compound names
    "getSmsDetailsReport":                       "se detaljeret SMS-rapport",
    "downloadMessageDraftReport":                "downloade rapport over besked-kladder",
    "getAllUsageReport":                         "se alle forbrugsrapporter",
    "getAllInvoicingReport":                     "se alle faktureringsrapporter",
    "finishBenchmark":                           "afslutte benchmark-periode",
    # GDPR
    "searchRightToBeForgotten":                  "søge efter ret-til-at-blive-glemt registreringer",
    "addRightToBeForgotten":                     "registrere ret til at blive glemt",
    "deleteRightToBeForgotten":                  "slette ret-til-at-blive-glemt registrering",
    # Nudging
    "getUserNudgingBlocks":                      "se nudging-indstillinger for bruger",
    "saveUserNudgingResponse":                   "gemme kanal-præference",
    # Social media
    "checkSocialMediaStatus":                    "se om sociale medier-forbindelsen er aktiv",
    "getSocialMediaAccounts":                    "tilknytte sociale medier-konti",
    "getSocialMediaAccountsAndAccessByProfile":  "tilknytte sociale medier-konti",
    # Internal/UI-context only — skip
    "getLastStatisticsCalculationDate":          None,
    "hasEboks":                                  None,
    "getProfiles":                               None,
    "getProfileRoles":                           None,
    "getProfilesByCustomer":                     None,
    "doesProfileHaveRole":                       None,
    "isPastSmsLogArchivingLimit":                None,
    "mapInvoiceReportDTOs":                      None,
    "getCurrentStateValue":                      None,
    "getCurrentProfileCache":                    None,
    "getProfileCache":                           None,
}

# ── Internal method pattern (never user-facing) ────────────────────────────────
_INTERNAL_RE = re.compile(
    r"^(getCurrentState|getCurrentProfile|getProfileCache|"
    r"localizeDateTime|formattedDateTime|formatFrom|formatedDate|"
    r"mapInvoiceReport|getAddressColumns|"
    r"createNotification|instant|"
    r"openConfirm|openConfirmWarning|"
    r"markAsPristine|setValidators|clearValidators|updateValueAndValidity|"
    r"setErrors|markForCheck|detectChanges|setValue|setDisabledState|"
    r"isPastSmsLogArchivingLimit)",
    re.IGNORECASE,
)

# ── Validation: words forbidden in output behavior text ───────────────────────
_FORBIDDEN_WORDS = {
    "component", "service", "method", "init", "fetch",
    "handler", "initialize", "observable", "lifecycle",
}
# Note: "load" and "subscribe" are avoided because they appear as prefixes in forbidden
# words check in validate_llm_output.py — use Danish instead.


# ── Helper functions ───────────────────────────────────────────────────────────

def camel_split(name: str) -> list[str]:
    """Split camelCase to lowercase word list.
    E.g. 'getUsageReport' → ['get', 'usage', 'report']
         'getTotalUsageCounts' → ['get', 'total', 'usage', 'counts']
    """
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1 \2", s)
    return [w.lower() for w in s.split() if w]


def build_entity(words: list[str]) -> str:
    """Translate entity word list to Danish phrase.
    Tries 2-word compounds first, then single words.
    """
    parts: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in ENTITY_SKIP:
            i += 1
            continue
        # Try 2-word compound
        if i + 1 < len(words):
            compound = w + words[i + 1]
            if compound in ENTITY_DA:
                parts.append(ENTITY_DA[compound])
                i += 2
                continue
        if w in ENTITY_DA:
            parts.append(ENTITY_DA[w])
        else:
            parts.append(w)
        i += 1
    return " ".join(parts)


def _is_valid_behavior(text: str) -> bool:
    """Check text passes the same rules as validate_llm_output.py:test_behavior_text."""
    if not text or len(text.strip()) < 5:
        return False
    if re.search(r"[a-z][A-Z]", text):  # camelCase
        return False
    if len(text.strip().split()) > 10:
        return False
    text_lower = text.lower()
    for w in _FORBIDDEN_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", text_lower):
            return False
    return True


def method_to_behavior(service_method: str, http_method: str = "GET") -> str | None:
    """Convert service method name → Danish user-facing behavior.

    Returns a string like "se beskeder på adresse" (without "Brugeren kan " prefix).
    Returns None if method should be skipped.
    """
    # Explicit override (None = skip)
    if service_method in EXPLICIT:
        return EXPLICIT[service_method]

    # Internal check
    if _INTERNAL_RE.match(service_method):
        return None

    words = camel_split(service_method)
    if not words:
        return None

    verb = words[0]
    entity_words = words[1:]

    action = VERB_DA.get(verb) or HTTP_VERB_DA.get(http_method, "behandle")

    entity_str = build_entity(entity_words)
    if not entity_str:
        return None

    return f"{action} {entity_str}"


# ── Words that indicate a behavior is about navigation (skip) ────────────────
_NAV_WORDS = {"back", "forward", "navigate", "route", "step", "next", "previous", "prev"}

# ── Words that are untranslated English in entity — discard behavior ──────────
_ENGLISH_ONLY_RE = re.compile(r"^[a-z][a-z0-9]{1,}$")  # lowercase English word
_KNOWN_DANISH_OR_OK = ENTITY_DA  # translations accepted as-is


def _has_untranslated(raw_phrase: str) -> bool:
    """Return True if phrase contains untranslated English words."""
    # Words after 'Brugeren kan <action>' — check entity part
    parts = raw_phrase.split()
    for p in parts:
        if _ENGLISH_ONLY_RE.match(p) and p not in ENTITY_SKIP and p not in ENTITY_DA.values():
            # Heuristic: if it's a short lowercase word not in our dicts, it's untranslated
            if len(p) <= 8 and not any(c in p for c in ("æ", "ø", "å", "-")):
                return True
    return False


def handler_to_behavior(handler: str) -> str | None:
    """Convert a click handler name → Danish behavior.
    E.g. 'onSearchClicked' → 'søge', 'downloadMessageDrafts' → 'downloade kladder'
    """
    # Explicit handler override first
    if handler in HANDLER_EXPLICIT:
        return HANDLER_EXPLICIT[handler]

    # Strip on/handle/do prefix
    name = HANDLER_STRIP_PREFIX.sub("", handler)
    # Strip Clicked/Click/Changed/Selected suffix
    name = HANDLER_STRIP_SUFFIX.sub("", name)

    if not name:
        return None

    # Skip pure navigation handlers
    words_lc = [w.lower() for w in camel_split(name)]
    if any(w in _NAV_WORDS for w in words_lc):
        return None

    result = method_to_behavior(name)
    # Reject if result contains untranslated English words
    if result and _has_untranslated(result):
        return None
    return result


# ── Core processing ────────────────────────────────────────────────────────────

def process_component(comp_name: str) -> dict | None:
    """Read evidence_pack.json and generate llm_output dict for one SMART component."""
    pack_path = RAW_DIR / comp_name / "evidence_pack.json"
    if not pack_path.exists():
        return None

    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  ERROR reading {comp_name}: {exc}", file=sys.stderr)
        return None

    comp_type = pack["meta"].get("type", "SMART")
    if comp_type == "DUMB":
        return None  # DUMB handled by auto_respond.py

    # ── Build lookup structures ───────────────────────────────────────────────
    shc = pack.get("service_http_calls") or []
    shc_by_method: dict[str, dict] = {h["service_method"]: h for h in shc if h.get("service_method")}

    method_graph: dict[str, list[str]] = pack.get("method_graph") or {}

    click_handlers: set[str] = {
        a["handler"]
        for a in (pack.get("template_actions") or [])
        if a.get("type") == "click" and a.get("handler")
    }

    # Build: service_method → click handler that triggers it (for VERIFIED_UI)
    svc_to_handler: dict[str, str] = {}
    for handler in click_handlers:
        for svc_method in (method_graph.get(handler) or []):
            if svc_method not in svc_to_handler:
                svc_to_handler[svc_method] = handler

    # ── Generate behaviors ────────────────────────────────────────────────────
    behaviors: list[dict] = []
    seen_raw: set[str] = set()  # deduplicate by raw action+entity phrase

    def _emit(raw_phrase: str, evidence_method: str | None = None) -> None:
        """Emit one behavior after building full text and validating."""
        if not raw_phrase:
            return
        full_text = f"Brugeren kan {raw_phrase}"
        norm = raw_phrase.lower().strip()
        if norm in seen_raw:
            return
        if not _is_valid_behavior(full_text):
            return
        seen_raw.add(norm)
        b: dict = {"text": full_text, "confidence": 0.85}
        if evidence_method:
            b["evidence_method"] = evidence_method
        behaviors.append(b)

    # 1. From service_http_calls (the backbone — all backend capabilities)
    for h in shc:
        sm = h.get("service_method", "")
        if not sm:
            continue
        raw = method_to_behavior(sm, h.get("http_method", "GET"))
        if raw:
            _emit(raw, svc_to_handler.get(sm))

    # 2. From click handlers directly (user-visible actions)
    #    These add VERIFIED_UI behaviors + catch handlers not in method_graph
    for handler in sorted(click_handlers):
        raw = handler_to_behavior(handler)
        if raw:
            _emit(raw, handler)

    if not behaviors:
        return None

    return {
        "behaviors":    behaviors,
        "flows":        [],   # validate_llm_output.py builds flows deterministically
        "requirements": [],   # validate_llm_output.py builds requirements deterministically
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def collect_components() -> list[str]:
    """Return list of component names to process."""
    if args.component:
        return [args.component]

    if args.all:
        # Scan raw-dir for all non-DUMB components
        names = []
        for d in sorted(RAW_DIR.iterdir()):
            if not d.is_dir():
                continue
            pack_path = d / "evidence_pack.json"
            if not pack_path.exists():
                continue
            try:
                meta = json.loads(pack_path.read_text(encoding="utf-8")).get("meta", {})
                if meta.get("type") not in ("DUMB",):
                    names.append(d.name)
            except Exception:
                pass
        return names

    # Fall back to component-list.json
    cl = Path(args.component_list)
    if not cl.exists():
        print(f"ERROR: not found: {cl}", file=sys.stderr)
        sys.exit(1)
    entries = json.loads(cl.read_text(encoding="utf-8-sig"))
    return [
        Path(e if isinstance(e, str) else e.get("filePath", "")).stem.replace(".component", "")
        for e in entries
    ]


def main() -> None:
    components = collect_components()
    if not components:
        print("No components to process.")
        return

    written = skipped = empty = errors = 0

    print(f"smart_harvester: processing {len(components)} component(s)  "
          f"[dry-run={args.dry_run}, overwrite={args.overwrite}]")
    print()

    for comp_name in components:
        out_path = RAW_DIR / comp_name / "llm_output.json"

        if out_path.exists() and not args.overwrite and not args.dry_run:
            skipped += 1
            continue

        result = process_component(comp_name)

        if result is None:
            empty += 1
            continue

        if args.dry_run:
            print(f"  [{comp_name}]  {len(result['behaviors'])} behaviors")
            for b in result["behaviors"]:
                em = f"  [VERIFIED via {b['evidence_method']}]" if b.get("evidence_method") else ""
                print(f"    • {b['text']}{em}")
            print()
        else:
            try:
                out_path.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                written += 1
            except Exception as exc:
                print(f"  ERROR writing {comp_name}: {exc}", file=sys.stderr)
                errors += 1

    print(f"Done — written: {written}  skipped: {skipped}  "
          f"empty (DUMB/no-calls): {empty}  errors: {errors}")


if __name__ == "__main__":
    main()
