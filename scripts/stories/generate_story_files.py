"""
generate_story_files.py
Genererer harvest/stories/MASTER.md + individuelle story-filer.

Kilder:
  - harvest/unified/user_stories.json  (US-001..048, fra Angular harvest)
  - Hardkodet liste over GreenAI DONE features (GS-001..021)

Output:
  - harvest/stories/MASTER.md
  - harvest/stories/US-001.md .. US-048.md
  - harvest/stories/GS-001.md .. GS-021.md
"""

# ─── BUILD GATE (non-bypassable) ────────────────────────────────────────────
import subprocess as _sp, sys as _sys, pathlib as _pl
_guard = _pl.Path(__file__).resolve().parents[2] / "scripts" / "guard" / "check_build_gate.py"
if _sp.run([_sys.executable, str(_guard)], check=False).returncode != 0:
    print("BUILD BLOCKED — guard returned BLOCK. See harvest/architect-review/build_state.json")
    _sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "harvest" / "stories"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. GreenAI DONE stories (GS-XXX) — bygget fra GREEN_AI_BUILD_STATE.md
# ---------------------------------------------------------------------------
GREENAI_STORIES = [
    {
        "id": "GS-001",
        "status": "DONE",
        "priority": "P0",
        "domain": "Auth",
        "title": "Login og token-fornyelse",
        "story_da": "Som bruger vil jeg logge ind med email/password og automatisk forny min session, så jeg kan tilgå systemet sikkert.",
        "acceptance_criteria": [
            "POST /api/auth/login returnerer JWT + refresh-token",
            "POST /api/auth/refresh fornyer token uden re-login",
            "POST /api/auth/logout ugyldiggør refresh-token",
            "GET /api/auth/me returnerer aktuel bruger",
        ],
        "impl": {
            "features": ["Auth/Login", "Auth/Me", "Auth/RefreshToken", "Auth/Logout"],
            "db_tables": ["Users", "UserRefreshTokens"],
            "notes": "Custom JWT — ICurrentUser. Ingen cookies.",
        },
    },
    {
        "id": "GS-002",
        "status": "DONE",
        "priority": "P0",
        "domain": "Auth",
        "title": "Adgangskode-styring",
        "story_da": "Som bruger vil jeg ændre min adgangskode og nulstille den via email, så jeg kan bevare kontrol over min konto.",
        "acceptance_criteria": [
            "POST /api/auth/change-password kræver nuværende kode",
            "POST /api/user-self-service/password-reset sender reset-email",
        ],
        "impl": {
            "features": ["Auth/ChangePassword", "UserSelfService/PasswordReset"],
            "db_tables": ["Users"],
            "notes": "Reset-flow via Email-domain (FatalEmailLogger fallback).",
        },
    },
    {
        "id": "GS-003",
        "status": "DONE",
        "priority": "P0",
        "domain": "Auth",
        "title": "Profil- og kundevalg",
        "story_da": "Som bruger vil jeg vælge kunde og profil ved login, så jeg arbejder i korrekt kontekst.",
        "acceptance_criteria": [
            "GET /api/auth/profile-context returnerer tilgængelige kunder/profiler",
            "POST /api/auth/select-customer sætter aktiv kunde",
            "POST /api/auth/select-profile sætter aktiv profil",
        ],
        "impl": {
            "features": ["Auth/GetProfileContext", "Auth/SelectCustomer", "Auth/SelectProfile"],
            "db_tables": ["Users"],
            "notes": "ICurrentUser opdateres i JWT-claim ved select.",
        },
    },
    {
        "id": "GS-004",
        "status": "DONE",
        "priority": "P1",
        "domain": "UserOnboarding",
        "title": "Bruger onboarding",
        "story_da": "Som administrator vil jeg invitere nye brugere, så de modtager velkomstkode og kan aktivere deres konto.",
        "acceptance_criteria": [
            "POST /api/user-onboarding opretter bruger og sender invitation",
            "INV_001/002/003 invarianter overholdes",
            "BEHAVIOR_TEST_PROOF 4/4 PASS",
        ],
        "impl": {
            "features": ["UserOnboarding/CreateUserOnboarding"],
            "db_tables": ["Users"],
            "notes": "🔒 LOCKED. Email-kanal til velkomst.",
        },
    },
    {
        "id": "GS-005",
        "status": "DONE",
        "priority": "P1",
        "domain": "AdminLight",
        "title": "Bruger- og rolleadministration",
        "story_da": "Som administrator vil jeg oprette brugere og tildele dem profiler og roller, så adgangsstyringen er korrekt.",
        "acceptance_criteria": [
            "POST /api/admin/create-user opretter bruger",
            "POST /api/admin/assign-profile tildeler profil",
            "POST /api/admin/assign-role tildeler rolle",
        ],
        "impl": {
            "features": ["AdminLight/CreateUser", "AdminLight/AssignProfile", "AdminLight/AssignRole"],
            "db_tables": ["Users"],
            "notes": "",
        },
    },
    {
        "id": "GS-006",
        "status": "DONE",
        "priority": "P1",
        "domain": "CustomerAdmin",
        "title": "Kundeadministration (read-side)",
        "story_da": "Som administrator vil jeg se kunder, profiler og brugere, så jeg kan overvåge og administrere adgang.",
        "acceptance_criteria": [
            "GET /api/customer-admin/settings returnerer kundeindstillinger",
            "GET /api/customer-admin/profiles returnerer profiler",
            "GET /api/customer-admin/users returnerer brugere",
        ],
        "impl": {
            "features": ["CustomerAdmin/GetCustomerSettings", "CustomerAdmin/GetProfiles", "CustomerAdmin/GetUsers"],
            "db_tables": ["Users"],
            "notes": "🔒 LOCKED.",
        },
    },
    {
        "id": "GS-007",
        "status": "DONE",
        "priority": "P2",
        "domain": "AdminLight",
        "title": "Systemindstillinger",
        "story_da": "Som administrator vil jeg læse og gemme systemindstillinger, så konfigurationen afspejler forretningsregler.",
        "acceptance_criteria": [
            "GET /api/admin/settings returnerer liste",
            "GET /api/admin/settings/{key} returnerer enkelt indstilling",
            "POST /api/admin/settings gemmer indstilling",
        ],
        "impl": {
            "features": ["AdminLight/ListSettings", "AdminLight/GetSetting", "AdminLight/SaveSetting"],
            "db_tables": [],
            "notes": "",
        },
    },
    {
        "id": "GS-008",
        "status": "DONE",
        "priority": "P2",
        "domain": "UserSelfService",
        "title": "Bruger selvbetjening",
        "story_da": "Som bruger vil jeg opdatere mine egne oplysninger og ændre min email, så mine kontaktdata er aktuelle.",
        "acceptance_criteria": [
            "PUT /api/user-self-service/update opdaterer brugerprofil",
            "POST /api/identity/change-email ændrer email",
        ],
        "impl": {
            "features": ["UserSelfService/UpdateUser", "Identity/ChangeUserEmail"],
            "db_tables": ["Users"],
            "notes": "🔒 DONE.",
        },
    },
    {
        "id": "GS-009",
        "status": "DONE",
        "priority": "P2",
        "domain": "ActivityLog",
        "title": "Aktivitetslog",
        "story_da": "Som system vil jeg logge bruger- og systemhændelser, så der er fuld audit trail.",
        "acceptance_criteria": [
            "POST /api/activity-log opretter log-entry",
            "POST /api/activity-log/batch opretter flere entries",
            "GET /api/activity-log returnerer logs",
        ],
        "impl": {
            "features": ["ActivityLog/CreateActivityLogEntry", "ActivityLog/CreateActivityLogEntries", "ActivityLog/GetActivityLogs"],
            "db_tables": ["ActivityLogs", "ActivityLogEntries", "ActivityLogEntryTypes"],
            "notes": "🔒 LOCKED.",
        },
    },
    {
        "id": "GS-010",
        "status": "DONE",
        "priority": "P1",
        "domain": "Email",
        "title": "Email afsendelse og gateway",
        "story_da": "Som system vil jeg sende transaktionelle emails og håndtere leveringsstatus fra gateway, så email-kanalen er pålidelig.",
        "acceptance_criteria": [
            "POST /api/email/send afsender email",
            "POST /api/email/send-system sender systemmail",
            "POST /api/email/gateway-dispatch dispatcher via gateway",
            "POST /api/email/webhook/status opdaterer leveringsstatus",
        ],
        "impl": {
            "features": ["Email/Send", "Email/SendSystem", "Email/GatewayDispatch", "Email/WebhookStatusUpdate"],
            "db_tables": ["EmailMessages", "EmailAttachments"],
            "notes": "🔒 CLOSED.",
        },
    },
    {
        "id": "GS-011",
        "status": "DONE",
        "priority": "P1",
        "domain": "Sms/Delivery",
        "title": "SMS afsendelse — outbox og DLR",
        "story_da": "Som system vil jeg afsende SMS via outbox-pattern og modtage leveringsstatus (DLR), så SMS-kanalen er pålidelig og sporbar.",
        "acceptance_criteria": [
            "OutboxWorker poller og afsender OutboundMessages",
            "TrackDelivery opdaterer status på OutboundMessages",
            "IngestGatewayApiDlr modtager DLR og opdaterer status",
            "State machine: Created→Queued→Sent→Delivered/Failed",
        ],
        "impl": {
            "features": ["Sms/Delivery/OutboxWorker", "Sms/Delivery/TrackDelivery", "Sms/Delivery/IngestGatewayApiDlr"],
            "db_tables": ["OutboundMessages", "Broadcasts"],
            "notes": "🔒 DONE GEN2. Outbox + DLR + state machine (2026-04-21).",
        },
    },
    {
        "id": "GS-012",
        "status": "DONE",
        "priority": "P2",
        "domain": "Sms/EboksIntegration",
        "title": "e-Boks integration",
        "story_da": "Som system vil jeg sende beskeder via e-Boks (Channel=3), så modtagere uden telefon kan nås.",
        "acceptance_criteria": [
            "EboksMessageProvider håndterer Channel=3",
            "Status sættes auto-delivered ved afsendelse",
        ],
        "impl": {
            "features": ["Sms/EboksIntegration/EboksMessageProvider"],
            "db_tables": ["OutboundMessages"],
            "notes": "🔒 DONE GEN2 (2026-04-21).",
        },
    },
    {
        "id": "GS-013",
        "status": "DONE",
        "priority": "P1",
        "domain": "Sms/ManageStandardReceiver",
        "title": "Standardmodtagere administration",
        "story_da": "Som administrator vil jeg oprette, opdatere og deaktivere standardmodtagere samt tilknytte grupper, keywords og distributionstelefoner, så modtagerlister er vedligeholdt.",
        "acceptance_criteria": [
            "CreateReceiver, UpdateReceiver, DeactivateReceiver",
            "AddGroup, AddKeyword, AddDistributionPhone",
            "MapToProfile",
        ],
        "impl": {
            "features": [
                "Sms/ManageStandardReceiver/CreateReceiver",
                "Sms/ManageStandardReceiver/UpdateReceiver",
                "Sms/ManageStandardReceiver/DeactivateReceiver",
                "Sms/ManageStandardReceiver/AddGroup",
                "Sms/ManageStandardReceiver/AddKeyword",
                "Sms/ManageStandardReceiver/AddDistributionPhone",
                "Sms/ManageStandardReceiver/MapToProfile",
            ],
            "db_tables": [],
            "notes": "🔒 DONE GEN2 (2026-04-21).",
        },
    },
    {
        "id": "GS-014",
        "status": "DONE",
        "priority": "P2",
        "domain": "Sms/Logging",
        "title": "SMS fejllogning (FatalEmailLogger)",
        "story_da": "Som system vil jeg logge fatale SMS-fejl via email fallback, så kritiske fejl ikke går tabt selv hvis primær logging fejler.",
        "acceptance_criteria": [
            "FatalEmailLogger sender email ved fatal SMS-fejl",
            "FAIL-OPEN: logger fejler ikke systemet",
        ],
        "impl": {
            "features": ["Sms/Logging/FatalEmailLogger"],
            "db_tables": [],
            "notes": "🔒 DONE GEN2. FAIL-OPEN pattern (2026-04-21).",
        },
    },
    {
        "id": "GS-015",
        "status": "DONE",
        "priority": "P1",
        "domain": "Conversations",
        "title": "Samtaler — oprettelse og svar",
        "story_da": "Som bruger vil jeg starte samtaler med modtagere og svare på indkommende beskeder, så tovejes kommunikation er mulig.",
        "acceptance_criteria": [
            "POST /api/conversations opretter ny samtale",
            "POST /api/conversations/{id}/reply sender svar",
            "BEHAVIOR_TEST_PROOF PASS",
        ],
        "impl": {
            "features": ["Conversations/CreateConversation", "Conversations/SendConversationReply"],
            "db_tables": ["Conversations", "ConversationMessages", "ConversationParticipants", "ConversationPhoneNumbers"],
            "notes": "N-B BUILD DONE.",
        },
    },
    {
        "id": "GS-016",
        "status": "DONE",
        "priority": "P1",
        "domain": "Conversations",
        "title": "Samtaler — læsning og ulæst-markering",
        "story_da": "Som bruger vil jeg se samtaleliste og beskeder samt markere samtaler som læst, så jeg har overblik over kommunikationen.",
        "acceptance_criteria": [
            "GET /api/conversations returnerer liste",
            "GET /api/conversations/{id}/messages returnerer beskeder",
            "POST /api/conversations/{id}/read markerer som læst",
        ],
        "impl": {
            "features": ["Conversations/ListConversations", "Conversations/GetConversationMessages", "Conversations/MarkConversationRead"],
            "db_tables": ["Conversations", "ConversationMessages"],
            "notes": "DONE (read-side D4).",
        },
    },
    {
        "id": "GS-017",
        "status": "DONE",
        "priority": "P1",
        "domain": "ConversationDispatch",
        "title": "Samtale-dispatch og status-opdatering",
        "story_da": "Som system vil jeg dispatche samtalemeddelelser via SMS-gateway og opdatere leveringsstatus, så samtale-beskeder er sporbare.",
        "acceptance_criteria": [
            "DispatchConversationMessage sender via gateway",
            "UpdateDeliveryStatus opdaterer ConversationMessages.Status",
            "ConversationDispatchJob kører periodisk",
        ],
        "impl": {
            "features": ["ConversationDispatch/DispatchConversationMessage", "ConversationDispatch/UpdateDeliveryStatus", "ConversationDispatch/ConversationDispatchJob"],
            "db_tables": ["ConversationMessages", "OutboundMessages"],
            "notes": "HARDENING DONE — afventer Architect GO.",
        },
    },
    {
        "id": "GS-018",
        "status": "DONE",
        "priority": "P2",
        "domain": "JobManagement",
        "title": "Job- og task-monitoring",
        "story_da": "Som administrator vil jeg se igangværende og seneste Azure Batch jobs samt modtage live-opdateringer, så jeg kan overvåge batchkørsler.",
        "acceptance_criteria": [
            "POST /api/jobs/log logger task-status",
            "GET /api/jobs/recent returnerer seneste/igangværende tasks",
            "GET /api/jobs/active SSE-stream med live job-events",
        ],
        "impl": {
            "features": ["JobManagement/LogJobTaskStatus", "JobManagement/GetRecentAndOngoingTasks", "JobManagement/ActiveJobs"],
            "db_tables": ["Jobs", "JobTasks", "JobTaskStatuses", "ClientEvents"],
            "notes": "🔒 LOCKED. Unified Azure Batch + in-process monitoring.",
        },
    },
    {
        "id": "GS-019",
        "status": "DONE",
        "priority": "P2",
        "domain": "Localization",
        "title": "Lokalisering og labels",
        "story_da": "Som system vil jeg hente og opdatere UI-labels, så brugergrænsefladen kan lokaliseres til dansk og andre sprog.",
        "acceptance_criteria": [
            "POST /api/localization/batch-upsert opdaterer labels",
            "GET /api/localization/labels returnerer labels pr. sprog",
        ],
        "impl": {
            "features": ["Localization/BatchUpsertLabels", "Localization/GetLabels"],
            "db_tables": ["Labels"],
            "notes": "🔒 LOCKED.",
        },
    },
    {
        "id": "GS-020",
        "status": "DONE",
        "priority": "P0",
        "domain": "System",
        "title": "System health og ping",
        "story_da": "Som infrastruktur vil jeg hurtigt verificere at applikationen kører korrekt, så load balancer og monitoring kan registrere problemer.",
        "acceptance_criteria": [
            "GET /api/health returnerer system-status",
            "GET /api/ping returnerer 200 OK",
        ],
        "impl": {
            "features": ["System/Health", "System/Ping"],
            "db_tables": [],
            "notes": "",
        },
    },
    {
        "id": "GS-021",
        "status": "DONE",
        "priority": "P2",
        "domain": "SharedKernel",
        "title": "Filtype-validering",
        "story_da": "Som system vil jeg validere uploadede filers type, så kun tilladte filformater accepteres.",
        "acceptance_criteria": [
            "IFileTypeValidationService validerer filtype",
            "FileTypeValidationService implementerer interface",
        ],
        "impl": {
            "features": ["SharedKernel/FileValidation/FileTypeValidationService"],
            "db_tables": [],
            "notes": "🔒 LOCKED. system_configuration.",
        },
    },
]

# ---------------------------------------------------------------------------
# ARCHITECT OVERRIDES — 2026-04-23 (LOCKED)
# Kilde: harvest/architect-review/architect_decisions_final.md
# ---------------------------------------------------------------------------

# Stories der DROPpes helt (ikke genereres)
DROP_IDS = {"US-043", "US-044", "US-045", "US-046", "US-047", "US-048", "US-NEW-08"}

# Stories der sættes til HOLD
HOLD_IDS = {"US-041"}

# Priority overrides: id → ny prioritet
PRIORITY_OVERRIDES = {
    # P1 → P2 (reduceret fra auto-P1)
    "US-005": "P2", "US-009": "P2", "US-012": "P2",
    "US-019": "P2", "US-020": "P2", "US-023": "P2",
    "US-032": "P2", "US-040": "P2",
    # P3 → P2 (oprykkede)
    "US-003": "P2", "US-004": "P2", "US-013": "P2",
    # Fastholdte P1 (ny US)
    "US-NEW-01": "P1", "US-NEW-07": "P1", "US-NEW-09": "P1",
    # P2 (ny US)
    "US-NEW-02": "P2", "US-NEW-06": "P2", "US-NEW-10": "P2",
}

# Title/capability renames: id → ny titel
TITLE_OVERRIDES = {
    "US-031": "SuperAdmin: Kundeliste (read-only)",
    "US-035": "Assign receiver to user/group",
    "US-038": "Manage Conversations",
}

# Domain overrides: id → (ny domain_da, ny domain)
DOMAIN_OVERRIDES = {
    "US-022": ("Address & Data", "Address & Data"),
    "US-038": ("Beskeder & Kommunikation", "Messaging & Communication"),
}

# Nye stories der tilføjes manuelt (ikke fra harvest JSON)
NEW_STORIES = [
    {
        "id": "US-NEW-01",
        "domain": "Messaging & Communication",
        "domain_da": "Beskeder & Kommunikation",
        "capability": "Se og sende email-beskeder",
        "resource": "email",
        "resource_da": "email",
        "verbs": ["GET", "POST"],
        "priority": "P1",
        "story_da": "Som bruger vil jeg se og sende email-beskeder, så jeg kan kommunikere med kunder via email-kanalen.",
        "acceptance_criteria": [
            "Brugeren ser liste over email-beskeder",
            "Brugeren kan oprette og sende ny email",
            "Leveringsstatus vises på sendte emails",
        ],
        "blazor": {
            "page": "Pages/messaging/EmailPage.razor",
            "route": "/messaging/email",
            "components": ["MudButton", "MudDataGrid", "MudDialog", "MudForm", "MudTextField"],
            "patterns": ["create-dialog", "list-with-search", "pagination"],
        },
        "source_behaviors": [
            {"text": "User can view email messages", "actor": "user", "classification": "VERIFIED"},
            {"text": "User can send email message", "actor": "user", "classification": "VERIFIED"},
        ],
    },
    {
        "id": "US-NEW-02",
        "domain": "System & Operations",
        "domain_da": "System & Drift",
        "capability": "Overvåg igangværende baggrundsjobs",
        "resource": "jobs",
        "resource_da": "baggrundsjobs",
        "verbs": ["GET"],
        "priority": "P2",
        "story_da": "Som administrator vil jeg se igangværende og seneste baggrundsjobs i realtid, så jeg kan overvåge systemets driftstilstand.",
        "acceptance_criteria": [
            "Administrator ser liste over aktive og seneste jobs",
            "Live-opdateringer via SSE uden reload",
            "Fejlede jobs markeres tydeligt",
        ],
        "blazor": {
            "page": "Pages/system/JobsPage.razor",
            "route": "/system/jobs",
            "components": ["MudDataGrid", "MudChip", "MudProgressLinear"],
            "patterns": ["sse-live-update", "list-with-search"],
        },
        "source_behaviors": [
            {"text": "System streams active job status via SSE", "actor": "system", "classification": "VERIFIED"},
        ],
    },
    {
        "id": "US-NEW-06",
        "domain": "Address & Data",
        "domain_da": "Adresser & Data",
        "capability": "Søg adresser på kort",
        "resource": "map",
        "resource_da": "kort",
        "verbs": ["GET", "POST"],
        "priority": "P2",
        "story_da": "Som bruger vil jeg søge adresser og se dem på et interaktivt kort, så jeg kan identificere og vælge geografiske modtagere.",
        "acceptance_criteria": [
            "Brugeren kan søge adresser via tekstindtastning",
            "Resultater vises på kort",
            "Brugeren kan vælge område og se modtagere",
        ],
        "blazor": {
            "page": "Pages/address/MapSearchPage.razor",
            "route": "/address/map",
            "components": ["MudTextField", "MudButton"],
            "patterns": ["map-view", "address-search"],
        },
        "source_behaviors": [
            {"text": "User can search addresses on map", "actor": "user", "classification": "VERIFIED"},
        ],
    },
    {
        "id": "US-NEW-07",
        "domain": "Messaging & Communication",
        "domain_da": "Beskeder & Kommunikation",
        "capability": "Forhåndsvisning af SMS-besked",
        "resource": "sms-preview",
        "resource_da": "SMS-forhåndsvisning",
        "verbs": ["GET"],
        "priority": "P1",
        "story_da": "Som bruger vil jeg se en forhåndsvisning af SMS-beskeden før afsendelse, så jeg kan verificere indhold og format.",
        "acceptance_criteria": [
            "Forhåndsvisning vises som mobil-visning",
            "Tegntæller vises",
            "Besked-segmentering vises",
        ],
        "blazor": {
            "page": "Shared/SmsPreview/SmsPreviewComponent.razor",
            "route": "(komponent)",
            "components": ["MudPaper", "MudText"],
            "patterns": ["preview-panel"],
        },
        "source_behaviors": [
            {"text": "User can preview SMS message before sending", "actor": "user", "classification": "VERIFIED"},
        ],
    },
    {
        "id": "US-NEW-09",
        "domain": "User & Access Management",
        "domain_da": "Brugere & Adgang",
        "capability": "Skift adgangskode",
        "resource": "password",
        "resource_da": "adgangskode",
        "verbs": ["POST"],
        "priority": "P1",
        "story_da": "Som bruger vil jeg kunne skifte min adgangskode, så jeg kan vedligeholde sikkerheden på min konto.",
        "acceptance_criteria": [
            "Brugeren kan indtaste nuværende + ny adgangskode",
            "Validering: ny kode opfylder krav",
            "Bekræftelse ved succesfuld ændring",
        ],
        "blazor": {
            "page": "Pages/account/ChangePasswordPage.razor",
            "route": "/account/change-password",
            "components": ["MudForm", "MudTextField", "MudButton"],
            "patterns": ["form-page"],
        },
        "source_behaviors": [
            {"text": "User can change own password", "actor": "user", "classification": "VERIFIED"},
        ],
    },
    {
        "id": "US-NEW-10",
        "domain": "Messaging & Communication",
        "domain_da": "Beskeder & Kommunikation",
        "capability": "Notifikations-log",
        "resource": "notification-log",
        "resource_da": "notifikationslog",
        "verbs": ["GET"],
        "priority": "P2",
        "story_da": "Som administrator vil jeg se en komplet log over hvad der er sendt til hvem, så jeg kan eftervise leverancer og opfylde compliance-krav.",
        "acceptance_criteria": [
            "Administrator ser log med afsender, modtager, kanal, status, tidspunkt",
            "Søg og filtrer på periode og status",
            "Eksport til CSV",
        ],
        "blazor": {
            "page": "Pages/messaging/NotificationLogPage.razor",
            "route": "/messaging/notification-log",
            "components": ["MudDataGrid", "MudDateRangePicker", "MudButton"],
            "patterns": ["list-with-search", "pagination"],
        },
        "source_behaviors": [
            {"text": "Administrator can view notification delivery log", "actor": "user", "classification": "INFERRED"},
        ],
    },
]

# ---------------------------------------------------------------------------
# 2. Helpers
# ---------------------------------------------------------------------------

STATUS_ICON = {"DONE": "✅", "READY": "🟡", "HOLD": "⏸️", "DROP": "🗑️"}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def status_icon(s):
    return STATUS_ICON.get(s, s)


def render_gs_file(story: dict) -> str:
    impl = story.get("impl", {})
    features = impl.get("features", [])
    db_tables = impl.get("db_tables", [])
    notes = impl.get("notes", "")

    ac_lines = "\n".join(f"- [ ] {c}" for c in story.get("acceptance_criteria", []))
    features_str = "\n".join(f"- `{f}`" for f in features) if features else "- (se GREEN_AI_BUILD_STATE.md)"
    db_str = ", ".join(f"`{t}`" for t in db_tables) if db_tables else "(ingen direkte)"

    return f"""# {story['id']}: {story['title']}

**Status:** {status_icon(story['status'])} {story['status']}
**Prioritet:** {story['priority']}
**Domain:** {story['domain']}
**Kilde:** GreenAI — allerede implementeret

---

## User Story

{story['story_da']}

---

## Acceptance Criteria

{ac_lines}

---

## Implementering (eksisterer)

### Features / Handlers
{features_str}

### DB Tabeller
{db_str}

### Noter
{notes if notes else '—'}

---

## Dependencies
- (se relaterede GS/US stories i MASTER.md)

---

*Sidst verificeret: GREEN_AI_BUILD_STATE.md — build 0 errors, alle tests PASS*
"""


def render_us_file(story: dict) -> str:
    blazor = story.get("blazor", {})
    components = ", ".join(f"`{c}`" for c in blazor.get("components", []))
    patterns = ", ".join(blazor.get("patterns", []))
    route = blazor.get("route", "TBD")
    page = blazor.get("page", "TBD")
    verbs = ", ".join(story.get("verbs", []))

    ac_lines = "\n".join(f"- [ ] {c}" for c in story.get("acceptance_criteria", []))

    behaviors = story.get("source_behaviors", [])
    beh_lines = "\n".join(
        f"- [{b.get('classification','?')}] {b.get('text','')} *(actor: {b.get('actor','')})*"
        for b in behaviors
    ) if behaviors else "- (ingen verificerede behaviors)"

    # Derive status from priority as default
    prio = story.get("priority", "P3")
    status = "READY" if prio in ("P0", "P1", "P2") else "HOLD"

    return f"""# {story['id']}: {story.get('capability', story['id'])} ({story.get('resource_da', '')})

**Status:** {status_icon(status)} {status}
**Prioritet:** {story['priority']}
**Domain:** {story.get('domain_da', story.get('domain', ''))}
**HTTP Verbs:** {verbs}
**Kilde:** Angular harvest → user story

---

## User Story

{story.get('story_da', '(ingen story tekst)')}

---

## Acceptance Criteria

{ac_lines}

---

## UI Implementation

| Felt | Værdi |
|------|-------|
| Page | `{page}` |
| Route | `{route}` |
| MudBlazor components | {components} |
| UI patterns | {patterns} |

---

## Backend (udfyldes af arkitekt)

| Felt | Værdi |
|------|-------|
| Endpoints | TBD |
| Handler(s) | TBD |
| SQL filer | TBD |
| DB Tabeller | TBD |

---

## Source Behaviors (fra harvest)

{beh_lines}

---

## Dependencies
- (udfyldes af arkitekt)

## Arkitekt-noter
- (tilføj her)
"""


def render_master(gs_stories: list, us_stories: list) -> str:
    lines = [
        "# MASTER — User Stories SSOT",
        "",
        "> **DRY/SSOT:** Alle user stories for GreenAI samlet — DONE (eksisterer) + READY/HOLD (skal bygges).",
        "> Arkitekten opdaterer status, prioritet og noter direkte i den individuelle story-fil.",
        "",
        f"**Sidst genereret:** 2026-04-23",
        f"**GreenAI DONE:** {len(gs_stories)} stories",
        f"**Harvest (ny UI):** {len(us_stories)} stories",
        f"**Total:** {len(gs_stories) + len(us_stories)} stories",
        "",
        "---",
        "",
        "## GreenAI — Eksisterende funktionalitet (DONE)",
        "",
        "| ID | Status | Prio | Domain | Titel |",
        "|----|--------|------|--------|-------|",
    ]
    for s in gs_stories:
        icon = status_icon(s["status"])
        lines.append(
            f"| [{s['id']}]({s['id']}.md) | {icon} {s['status']} | {s['priority']} | {s['domain']} | {s['title']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Harvest — Ny UI funktionalitet (READY/HOLD)",
        "",
        "| ID | Status | Prio | Domain | Capability | Route | Verbs |",
        "|----|--------|------|--------|-----------|-------|-------|",
    ]

    # Group by domain for readability
    domain_order = []
    seen = set()
    for s in us_stories:
        d = s.get("domain_da", s.get("domain", ""))
        if d not in seen:
            domain_order.append(d)
            seen.add(d)

    for domain in domain_order:
        domain_stories = [s for s in us_stories if s.get("domain_da", s.get("domain", "")) == domain]
        lines.append(f"| **{domain}** | | | | | | |")
        for s in domain_stories:
            prio = s.get("priority", "P3")
            status = "READY" if prio in ("P0", "P1", "P2") else "HOLD"
            icon = status_icon(status)
            route = s.get("blazor", {}).get("route", "TBD")
            verbs = ", ".join(s.get("verbs", []))
            cap = s.get("capability", "")
            lines.append(
                f"| [{s['id']}]({s['id']}.md) | {icon} {status} | {prio} | {domain} | {cap} | `{route}` | {verbs} |"
            )

    lines += [
        "",
        "---",
        "",
        "## Prioritets-oversigt",
        "",
        "| Prio | GreenAI DONE | Harvest READY | Harvest HOLD |",
        "|------|-------------|--------------|-------------|",
    ]

    for prio in ["P0", "P1", "P2", "P3"]:
        gs_count = sum(1 for s in gs_stories if s["priority"] == prio)
        us_ready = sum(1 for s in us_stories if s["priority"] == prio and prio in ("P0", "P1", "P2"))
        us_hold = sum(1 for s in us_stories if s["priority"] == prio and prio == "P3")
        lines.append(f"| {prio} | {gs_count} | {us_ready} | {us_hold} |")

    lines += [
        "",
        "---",
        "",
        "## Sådan bruges dette dokument",
        "",
        "1. **Arkitekt:** Åbn individuelle story-filer (GS-*/US-*) for detaljer",
        "2. **Byg-ordre:** Udfyld `harvest/architect-review/04_build_order.md` med WAVE 1-4 baseret på prioritet",
        "3. **Status-opdatering:** Ændr `Status:` i individuel story-fil når feature bygges/afsluttes",
        "4. **Ny story:** Tilføj ny `.md`-fil i dette katalog + tilføj række i denne MASTER",
        "5. **SSOT-regel:** Arkitektur-beslutninger skrives i story-filen — IKKE i chat",
        "",
        "---",
        "",
        "*Genereret af `scripts/stories/generate_story_files.py`*",
    ]
    return "\n".join(lines) + "\n"


def render_readme(gs_stories: list, us_stories: list) -> str:
    from datetime import date
    today = date.today().isoformat()
    total = len(gs_stories) + len(us_stories)
    p1 = sum(1 for s in us_stories if s.get("priority") == "P1")
    p2 = sum(1 for s in us_stories if s.get("priority") == "P2")
    p3 = sum(1 for s in us_stories if s.get("priority") == "P3")
    return f"""# README — Story-katalog

> **Start her** før du åbner andre filer.

**Genereret:** {today}
**Total stories:** {total} ({len(gs_stories)} DONE + {len(us_stories)} aktive)

---

## Filer i dette katalog

| Fil | Indhold |
|-----|---------|
| **MASTER.md** | Komplet oversigt — alle stories, status, prio, links |
| **GS-001..021.md** | GreenAI eksisterende funktionalitet (✅ DONE) |
| **US-xxx.md** | Ny UI funktionalitet fra harvest |
| **US-NEW-xx.md** | Manuelt tilføjede stories (arkitekt-besluttet) |

---

## Prioritetsoversigt (harvest stories)

| Prio | Antal |
|------|-------|
| P1 | {p1} |
| P2 | {p2} |
| P3 | {p3} |

---

## Procedure

1. **Arkitekt:** Læs `MASTER.md` → åbn individuelle filer via links
2. **Build:** Se `harvest/architect-review/build_order.md` for WAVE-rækkefølge
3. **Status-opdatering:** Ændr `Status:` i individuel story-fil
4. **Ny story:** Tilføj i `generate_story_files.py` → regenerér
5. **SSOT-regel:** Kilde = denne mappe + generator-script — IKKE temp/

---

*Genereret af `scripts/stories/generate_story_files.py`*
"""


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------

def main():
    # Load harvest stories
    stories_path = ROOT / "harvest" / "unified" / "user_stories.json"
    if not stories_path.exists():
        print(f"ERROR: {stories_path} ikke fundet", file=sys.stderr)
        sys.exit(1)

    with open(stories_path, encoding="utf-8") as f:
        data = json.load(f)

    us_stories_raw = data.get("user_stories", data.get("stories", []))
    print(f"Loaded {len(us_stories_raw)} harvest stories")

    # Apply architect overrides to harvest stories
    us_stories = []
    dropped = []
    for s in us_stories_raw:
        sid = s["id"]
        if sid in DROP_IDS:
            dropped.append(sid)
            continue
        # Apply priority override
        if sid in PRIORITY_OVERRIDES:
            s = dict(s)
            s["priority"] = PRIORITY_OVERRIDES[sid]
        # Apply title/capability override
        if sid in TITLE_OVERRIDES:
            s = dict(s)
            s["capability"] = TITLE_OVERRIDES[sid]
        # Apply domain override
        if sid in DOMAIN_OVERRIDES:
            s = dict(s)
            s["domain_da"], s["domain"] = DOMAIN_OVERRIDES[sid]
        us_stories.append(s)

    # Append new stories
    for s in NEW_STORIES:
        if s["id"] not in DROP_IDS:
            us_stories.append(s)

    print(f"After overrides: {len(us_stories)} active, {len(dropped)} dropped")

    # Write GS files
    for s in GREENAI_STORIES:
        path = OUT_DIR / f"{s['id']}.md"
        path.write_text(render_gs_file(s), encoding="utf-8")
    print(f"Written {len(GREENAI_STORIES)} GS-files")

    # Write US files (incl. new stories)
    for s in us_stories:
        sid = s["id"]
        path = OUT_DIR / f"{sid}.md"
        # HOLD stories get special status in file
        if sid in HOLD_IDS:
            content = render_us_file(s).replace(
                "**Status:** 🟡 READY", "**Status:** ⏸️ HOLD"
            ).replace(
                "**Status:** ⏸️ HOLD\n**Status:** ⏸️ HOLD", "**Status:** ⏸️ HOLD"
            )
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(render_us_file(s), encoding="utf-8")
    print(f"Written {len(us_stories)} US-files")

    # Write MASTER
    master_path = OUT_DIR / "MASTER.md"
    master_path.write_text(render_master(GREENAI_STORIES, us_stories), encoding="utf-8")
    print(f"Written MASTER.md")

    # Write README (arkitekt-indeks)
    readme_path = OUT_DIR / "README.md"
    readme_path.write_text(render_readme(GREENAI_STORIES, us_stories), encoding="utf-8")
    print(f"Written README.md")

    print(f"\nDone — {len(GREENAI_STORIES) + len(us_stories)} story-filer i {OUT_DIR}")


if __name__ == "__main__":
    main()
