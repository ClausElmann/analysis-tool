# Pipeline Architecture: Analysis → UI → E2E → Journey → Demo

> Generated: 2026-04-08  
> Basis: fuld scan af analysis-tool (domains/, data/, docs/, analyzers/, core/)  
> Mode: STRICT — kun verificerede data, aldrig gættet

---

## 1. Hvad analysis-tool faktisk indeholder

```json
{
  "entities": {
    "source": "domains/*/010_entities.json",
    "quality": "mixed",
    "note": "Mest bare navne-lister. identity_access: fulde feltbeskrivelser. messaging/customer_admin: bare klassenavne.",
    "usable_domains": ["identity_access", "customer_administration"],
    "unusable_domains": ["messaging (entities = name-list only)", "address_management", "recipient_management"]
  },

  "flows": {
    "source": "domains/*/030_flows.json",
    "quality": "HIGH for identity_access, LOW for all others",
    "richest": {
      "identity_access": [
        "FLOW_001: EmailPasswordLogin (trigger, happy_path, 4 branches)",
        "FLOW_002: AzureADLogin (MSAL, silent SSO)",
        "FLOW_003: 2FA PIN Verification (3 delivery methods)",
        "FLOW_004: TokenRefresh (sliding window, concurrency risk)",
        "FLOW_005: PasswordReset (token-based, 7 steps)",
        "FLOW_006: StandardReceiverSend",
        "FLOW_007: UserProfileUpdate"
      ],
      "messaging": ["WizardStep (ONLY — 1 entry, no structure)"],
      "customer_administration": ["3 event handlers — NOT flows"],
      "recipient_management": ["2 processor names — NOT flows"]
    }
  },

  "ui_patterns": {
    "source": "docs/UI_MODEL_*.json (MANUALLY CURATED — ikke auto-genereret)",
    "files": [
      "UI_MODEL_BROADCASTING.json — hub med 6 panels, roles, actions",
      "UI_MODEL_MESSAGE_WIZARD.json — 5 flow-nodes med conditions + 3 variants",
      "UI_MODEL_STATUS.json — tabbed list med filters",
      "UI_MODEL_CUSTOMER_ADMIN.json — tabbed admin med CRUD",
      "UI_MODEL_SUPER_ADMIN_CONTEXT.json — context-aware selector",
      "NAVIGATION_MODEL.json — capabilities + context model (profile-implicit vs super-admin-explicit)"
    ],
    "quality": "HIGH — dette er den rigeste og mest actionable data i hele tool'et"
  },

  "actions": {
    "source": "domains/*/020_behaviors.json",
    "quality": "HIGH for identity_access (10 behaviors), EMPTY for messaging/customer_admin",
    "usable": [
      "BEH_001: EmailPasswordLogin (7 steps, lockout rule)",
      "BEH_002: RefreshAccessToken (5 steps)",
      "BEH_003: Logout (server-side invalidation)",
      "BEH_004: AzureADLogin",
      "BEH_005: TwoFactorAuthentication (slide states 0-5)",
      "BEH_006: PasswordReset",
      "BEH_007: ProfileSelection (HTTP 300 flow)",
      "BEH_008: ImpersonationMode",
      "BEH_009: UserUpdate",
      "BEH_010: AccountLockout (time-scaled)"
    ]
  },

  "screens": {
    "source": "data/angular_entries.json + docs/NAVIGATION_MODEL.json",
    "critical_gap": "angular_entries.json har EMPTY paths for alle routes — angular_analyzer.py kan ikke ekstrahere URL-paths",
    "usable_source": "NAVIGATION_MODEL.json (manuelt kurateret)",
    "screens_from_navigation_model": [
      "/broadcasting (hub)",
      "/message-wizard/{step} (3 variants: standard, scheduled, stencil)",
      "/status (tabbed: sent, scheduled, failed, archived)",
      "/status/{id} (detail)",
      "/drafts",
      "/customer-admin (tabbed: users, profiles, labels, settings)",
      "/admin/users",
      "/admin/settings",
      "/admin/super (context-selector: country→customer→profile)",
      "/user/profile",
      "/select-customer",
      "/select-profile"
    ]
  },

  "domain_completeness": {
    "identity_access": 0.98,
    "customer_administration": 0.88,
    "activity_log": 0.92,
    "profile_management": "UNKNOWN (not scanned)",
    "messaging": 0.47,
    "address_management": 0.58,
    "recipient_management": "LOW (only processor names)",
    "total_domains": 37,
    "locked_reference": "product_scope (completeness=1.0, read-only)"
  }
}
```

---

## 2. UI Mapping — Analysis Data → Blazor Pages + Components

```json
{
  "ui_mapping": {
    "entity_to_page": {
      "User (identity_access/010_entities.json)": {
        "page": "/user/profile",
        "component": "UserProfilePage.razor",
        "fields": ["Email", "Name", "PhoneNumber", "TimeZoneId", "LanguageId", "ResetPhone", "PhoneCode"],
        "source_quality": "HIGH — alle felter verificerede fra User.cs",
        "gap": "AuthenticatorSecret vises IKKE til bruger (TOTP setup mangler UI)"
      },
      "UserRefreshToken (identity_access/010_entities.json)": {
        "page": "ingen — intern session state",
        "component": "ingen",
        "note": "Håndteres af middleware, ikke UI"
      },
      "SmsGroup (docs/PRODUCT_CAPABILITY_MAP.json)": {
        "page": "/status + /status/{id}",
        "component": "StatusPage.razor + StatusDetailPage.razor",
        "note": "Ikke en 1:1 entity-til-page — broadcast er primær forretningsenhed",
        "source_quality": "ADAPTED — UI_MODEL_STATUS.json beskriver visning, ikke entity"
      }
    },

    "flow_to_screen": {
      "FLOW_001 EmailPasswordLogin": {
        "screen": "LoginPage → DashboardPage",
        "blazor_route": "/auth/login → /dashboard",
        "slide_states_in_angular": "6 states (0=login, 1=PIN, 2=method, 3=forgot, 4=confirm, 5=TOTP)",
        "green_ai_approach": "Separate pages per state (ikke slide-in-place)",
        "status": "✅ implementeret (LoginFlowE2ETests passing)"
      },
      "FLOW_002 AzureADLogin": {
        "screen": "LoginPage (MSAL button)",
        "green_ai_approach": "DEFERRED — ikke scope for current phase",
        "source_quality": "HIGH — MSAL flow dokumenteret"
      },
      "FLOW_003 2FA": {
        "screen": "UNKNOWN — ingen UI-side implementeret endnu",
        "source_quality": "HIGH — slide states dokumenterede",
        "gap": "Kræver: /auth/2fa route + PinEntryPage + MethodSelectionPage"
      },
      "FLOW_005 PasswordReset": {
        "screen": "UNKNOWN — ingen UI-side implementeret",
        "flow_steps": ["forgot-pw → email → /auth/reset-password?token= → new-pw form → login"],
        "backend": "✅ UserSelfService/PasswordReset/ handler eksisterer",
        "gap": "PasswordResetPage.razor mangler — Slice 22"
      },
      "WizardStep (messaging/030_flows.json)": {
        "note": "UNUSABLE DATA — kun 'WizardStep' som string. Rigtig data er i UI_MODEL_MESSAGE_WIZARD.json",
        "actual_source": "UI_MODEL_MESSAGE_WIZARD.json — 5 nodes, 3 variants, state podmaps"
      }
    },

    "actions_to_buttons": {
      "BEH_001 steps → login form": {
        "buttons": ["Login (primary)", "Glemt adgangskode (link)"],
        "validation": "after submit — ikke per-felt"
      },
      "BEH_003 Logout": {
        "button": "Log ud (i app shell / profil dropdown)",
        "result": "POST /api/user/logout → redirect til /auth/login"
      },
      "BEH_006 PasswordReset": {
        "buttons": ["Send reset email", "Gem ny adgangskode"],
        "form_fields": ["Email (trin 1)", "Ny adgangskode + bekræft (trin 2)"]
      },
      "FLOW_004 TokenRefresh": {
        "note": "INGEN UI-knap — håndteres af HTTP interceptor i baggrunden"
      },
      "UI_MODEL_BROADCASTING panels → buttons": {
        "send-methods grid": "6 metode-kort → hvert starter wizard på specifikt trin",
        "scenarios": "Start-knap per scenario (forududfyld wizard)",
        "unapproved-messages": "Godkend-knap per besked",
        "quick-send": "Send-knap (direkte, ingen wizard)"
      }
    }
  }
}
```

---

## 3. E2E Test Mapping — Flows → Playwright Tests

```json
{
  "e2e_mapping": {
    "flow_to_test": {
      "FLOW_001 EmailPasswordLogin": {
        "test_class": "LoginFlowE2ETests.cs",
        "facts": 5,
        "coverage": "✅ happy path + SelectCustomer + SelectProfile",
        "missing": ["lockout flow (BEH_010)", "invalid credentials explicit assert"]
      },
      "FLOW_003 2FA": {
        "test_class": "MANGLER",
        "coverage": "❌ null coverage",
        "blocker": "Ingen UI-side, ingen testdata med 2FA aktiveret"
      },
      "FLOW_005 PasswordReset": {
        "test_class": "MANGLER",
        "coverage": "❌ null coverage",
        "blocker": "PasswordResetPage.razor eksisterer ikke endnu"
      },
      "UI_MODEL_MESSAGE_WIZARD flow": {
        "test_class": "DemoFlowTests.cs (visuelt) + MANGLER funktionel",
        "coverage": "step 1-2 visuelt, step 3-4 ❌",
        "note": "UI_MODEL_MESSAGE_WIZARD.json har ALLE 5 nodes med conditions — klar til test-generering"
      },
      "UI_MODEL_BROADCASTING panels": {
        "test_class": "NavigationVisualTests.cs (visuelt)",
        "coverage": "✅ visuel, ❌ ingen funktionel (send-methods click → wizard navigation)"
      }
    },

    "action_to_selector": {
      "BEH_001 login": {
        "selectors": {
          "email_field": "[data-testid='login-email']",
          "password_field": "[data-testid='login-password']",
          "submit": "[data-testid='login-submit']",
          "error": "[data-testid='login-error']"
        },
        "source": "LoginFlowE2ETests.cs — verificerede selectors"
      },
      "UI_MODEL_BROADCASTING panels": {
        "send_methods_grid": "[data-testid='send-methods-grid']",
        "method_card": "[data-testid='method-card-by-address']",
        "note": "data-testids fra DemoFlowTests.cs — verificerede mod Razor-kode"
      },
      "UI_MODEL_MESSAGE_WIZARD nodes": {
        "wizard_step": "[data-testid='wizard-step-{N}']",
        "note": "ANTAGELSE — selectors ikke verificerede for step 3+4",
        "blocker": "Kræver inspektion af SendWizardPage.razor step 3-4"
      }
    },

    "validation_points": [
      {
        "flow": "FLOW_001",
        "point": "JWT stored after login",
        "how": "localStorage assertion OR redirected to /dashboard"
      },
      {
        "flow": "FLOW_001 branch_300",
        "point": "SelectProfile shown when multiple profiles",
        "how": "E2EDatabaseFixture seeder skaber 2 profiles — LoginFlow tester allerede dette"
      },
      {
        "flow": "FLOW_005",
        "point": "Reset email sendt (mock send i test)",
        "how": "UNKNOWN — kræver test-SMTP mock eller afskæring af email-service"
      },
      {
        "flow": "MessageWizard confirm step",
        "point": "Recipient count > 0 på confirm-skærm",
        "how": "[data-testid='confirm-recipient-count'] inner text assertion"
      }
    ]
  }
}
```

---

## 4. Customer Journey Mapping — Flows → Journeys

```json
{
  "journeys": [
    {
      "name": "Ny operatør — første login og broadcast",
      "persona": "Kommunal sagsbehandler, første dag",
      "data_source": "FLOW_001 + UI_MODEL_BROADCASTING + UI_MODEL_MESSAGE_WIZARD",
      "steps": [
        "Modtager velkomst-email med midlertidig adgangskode",
        "Navigerer til login-siden",
        "Indtaster email + midlertidig kode → tvinges til at skifte kode",
        "Lander på /broadcasting (hub)",
        "Ser send-metode gitter — klikker 'Send til adresser'",
        "Wizard åbner på trin 1 (adressevalg)",
        "Vælger gadeadresse via søgning",
        "Wizard trin 2: skriver beskedtekst (SMS + email kanal)",
        "Wizard trin 3: review — ser 47 modtagere, forhåndsvisning",
        "Klikker 'Send nu'",
        "Status-page viser: '47 beskedder i kø'"
      ],
      "story": [
        "Jesper er ny medarbejder i Vejle Kommune.",
        "Han har aldrig sendt en advarsel til borgere digitalt.",
        "I dag er der gaslugt ved Torvet — han skal nå 300 husstande inden for 15 minutter.",
        "Han logger ind, vælger adresseområde på kortet, skriver én linje tekst, og sender.",
        "47 sekunder fra login til afsendelse."
      ],
      "demo_potential": "HIGH — tydelig start/slut, dramatisk kontekst (nødsituation)",
      "data_gaps": [
        "Ingen brugerdata for 'ny bruger tvinges til kodeændring' i analysis-tool",
        "Adressevalg UI-model mangler (address_management completeness=0.58)"
      ]
    },
    {
      "name": "Status-opfølgning — hvem fik ikke beskeden?",
      "persona": "Erfaren operatør, dagen efter broadcast",
      "data_source": "UI_MODEL_STATUS.json + domains/activity_log",
      "steps": [
        "Logger ind → /broadcasting",
        "Klikker 'Status' i navigation",
        "StatusPage åbner på 'Sendt' tab",
        "Filtrerer på gårsdagens broadcast",
        "Klikker på broadcast-rækken",
        "StatusDetailPage: ser 3 fejlede leveringer",
        "Klikker 'Gensend til fejlede'",
        "Bekræfter dialog → 3 gensendinger queued"
      ],
      "story": [
        "Lone fulgte op på varslingsbeskederne fra i går.",
        "3 mobilnumre var udgåede — de fik aldrig beskeden.",
        "Med to klik gensendte hun til dem via email i stedet."
      ],
      "demo_potential": "MEDIUM — viser product value (opfølgning + gensend)",
      "data_gaps": [
        "UI_MODEL_STATUS.json — delvist verificeret fra NavigationVisualTests",
        "Gensend-flow (ResendDialog) er verificeret via DetailPageE2ETests"
      ]
    },
    {
      "name": "Customer Admin — ny bruger onboarding",
      "persona": "Teamleder / administrator",
      "data_source": "UI_MODEL_CUSTOMER_ADMIN.json + CustomerAdminE2ETests",
      "steps": [
        "Navigerer til /customer-admin",
        "Users-tab: klikker 'Opret bruger'",
        "Udfylder email + navn",
        "Vælger profil (profil 2: begrænset adgang)",
        "Gemmer → ny bruger vises i listen",
        "Klikker ny bruger → UserDetail",
        "Tilknytter yderligere roller"
      ],
      "story": [
        "Maria har ansat en ny kollega.",
        "Hun sætter ham op med kun SMS-adgang — han skal ikke se indgående beskeder endnu.",
        "5 minutter fra oprettelse til første login."
      ],
      "demo_potential": "LOW — admin-flow, ikke kerneprodukt",
      "data_gaps": []
    }
  ]
}
```

---

## 5. Demo Engine Mapping — Journeys → Video

```json
{
  "demo_mapping": {
    "journey_to_video": {
      "Ny operatør — første login og broadcast": {
        "target_file": "demo-journey-1-broadcast.mp4",
        "estimated_duration_sec": 120,
        "segments": [
          { "id": "seg_1", "scene": "login", "highlights": ["[data-testid='login-email']", "[data-testid='login-submit']"], "voice": "Jesper logger ind med sin nye adgangskode." },
          { "id": "seg_2", "scene": "broadcasting_hub", "highlights": ["[data-testid='send-methods-grid']", "[data-testid='method-card-by-address']"], "voice": "Hubben viser alle tilgængelige afsendelsesmetoder." },
          { "id": "seg_3", "scene": "wizard_step1", "highlights": ["[data-testid='address-search']"], "voice": "Han søger efter det berørte gadeafsnit." },
          { "id": "seg_4", "scene": "wizard_step2", "highlights": ["[data-testid='message-text-input']"], "voice": "En kort SMS-besked til borgerne." },
          { "id": "seg_5", "scene": "wizard_confirm", "highlights": ["[data-testid='confirm-recipient-count']", "[data-testid='confirm-send']"], "voice": "47 modtagere bekræftet. Afsender." },
          { "id": "seg_6", "scene": "status_page", "highlights": ["[data-testid='status-list-table']"], "voice": "Beskederne er nu i kø til levering." }
        ],
        "blocker": "wizard step 3-4 selectors ikke verificerede; address-search selector ukendt"
      }
    },

    "step_to_highlight": {
      "login_email_input": {
        "selector": "[data-testid='login-email']",
        "source": "verificeret fra LoginFlowE2ETests.cs",
        "highlight_duration_ms": 3000
      },
      "method_card_by_address": {
        "selector": "[data-testid='method-card-by-address']",
        "source": "verificeret fra DemoFlowTests.cs",
        "highlight_duration_ms": 3000
      },
      "wizard_confirm_button": {
        "selector": "UNKNOWN",
        "source": "mangler — step 3-4 ikke implementeret/testet",
        "highlight_duration_ms": 3000
      },
      "status_table": {
        "selector": "[data-testid='status-list-table']",
        "source": "verificeret fra PageVisualTests.cs",
        "highlight_duration_ms": 2000
      }
    },

    "story_to_voice": {
      "engine": "Azure Cognitive Services TTS",
      "voice": "da-DK-ChristelNeural",
      "script_source": "Journeys[].story[] → scripts/demo/generate-script.ps1",
      "format": "SSML med <break> tags og <prosody rate='slow'>",
      "verified_working": true,
      "example_verified": "test-voice.ps1 + DemoFlowTests.cs → demo-test.mp4"
    }
  }
}
```

---

## 6. Pipeline Arkitektur — Den samlede kæde

### Nuværende state (verificeret)

```
analysis-tool/domains/{domain}/030_flows.json   ← HIGH quality for identity_access
analysis-tool/docs/UI_MODEL_*.json              ← HIGH quality (manuelt kurateret)
analysis-tool/docs/NAVIGATION_MODEL.json        ← HIGH quality
analysis-tool/data/angular_entries.json         ← LOW quality (empty paths)
analysis-tool/data/component_api_map.json       ← LOW quality (4 entries)
```

### Foreslået pipeline (REALISTISK — baseret på hvad data faktisk kan levere)

```
TIER 1: Verificeret data (kørbar pipeline i dag)
──────────────────────────────────────────────────
domains/identity_access/030_flows.json
    └─► Flow-JSON med trigger + steps + branches
         └─► [GENERATOR] FlowToE2ETest.py
              └─► Playwright test-skeleton (.cs)
                  (mangler: data-testid mapping)

docs/UI_MODEL_*.json
    └─► Page structure med panels + actions + roles
         └─► [GENERATOR] UIModelToBlazorPage.py
              └─► Page.razor skeleton + parameter types
                  (mangler: Blazor-kode, kun struktur)

docs/UI_MODEL_MESSAGE_WIZARD.json (flow-nodes)
    └─► Journey steps med conditions + branches
         └─► [GENERATOR] JourneyBuilder.py
              └─► Customer journey JSON
                   └─► VoiceScript.py → SSML narration
                        └─► DemoFlowTest.cs → MP4

TIER 2: Mangler (kan ikke genereres i dag)
──────────────────────────────────────────
address_management flows → mangler (completeness 0.58)
messaging flows → mangler (completeness 0.47, ingen structure)
angular_entries routes → mangler (alle paths er "")
```

```json
{
  "architecture": {
    "source_of_truth": {
      "primary": "analysis-tool/docs/UI_MODEL_*.json — eneste kilde med structure + roles + actions",
      "secondary": "analysis-tool/domains/identity_access/ — eneste domain med fulde flows + rules",
      "tertiary": "analysis-tool/docs/NAVIGATION_MODEL.json — screen inventory + context model",
      "NOT_usable": "data/angular_entries.json (empty paths), data/ui_coverage_report.json (empty)"
    },

    "pipelines": [
      {
        "name": "flow_to_e2e",
        "input": "domains/{domain}/030_flows.json",
        "transform": "FlowToE2ETest.py (ny — se slice_A)",
        "output": "tests/GreenAi.E2E/{Feature}E2ETests.cs (skeleton)",
        "viable_domains_today": ["identity_access"],
        "blocked_domains": ["messaging (ingen flows)", "address_management (sparse)"]
      },
      {
        "name": "ui_model_to_page",
        "input": "docs/UI_MODEL_*.json",
        "transform": "UIModelToRazor.py (ny — se slice_B)",
        "output": "src/GreenAi.Api/Components/Pages/{Page}/Index.razor (skeleton)",
        "viable_today": ["broadcasting", "message-wizard", "status", "customer-admin"],
        "gap": "Genererer kun struktur — ikke handler-calls eller DI"
      },
      {
        "name": "journey_to_demo",
        "input": "journeys JSON (fra denne doc) + data-testids fra E2E tests",
        "transform": "JourneyToDemo.py (ny — se slice_C)",
        "output": "scripts/demo/generate-script.ps1 input + DemoFlowTest scenario",
        "viable_today": "journey 1 (login→broadcast) — PARTIAL (wizard step 3-4 mangler)",
        "full_viable": "efter Slice 23 (wizard E2E) + adresse-selector implementering"
      },
      {
        "name": "rules_to_tests",
        "input": "domains/identity_access/070_rules.json",
        "transform": "RulesToUnitTests.py (ny — se slice_D)",
        "output": "tests/GreenAi.Tests/{Domain}/{Rule}Tests.cs",
        "viable_today": ["RULE_001 PasswordLockout", "RULE_002 AccessTokenTTL", "RULE_003 AutoProfileSelection", "RULE_004 PasswordHashing", "RULE_006 SoftDelete"]
      }
    ],

    "data_flow": [
      "analysis-tool/domains/*/030_flows.json",
      "  → flow_to_e2e pipeline → E2E test skeletons",
      "  → journey_builder → customer journeys",
      "  → journey_to_demo → voice scripts + demo test cases",
      "",
      "analysis-tool/docs/UI_MODEL_*.json",
      "  → ui_model_to_page pipeline → Blazor page skeletons",
      "  → journey_builder → UI steps med selectors",
      "",
      "analysis-tool/domains/*/070_rules.json",
      "  → rules_to_tests pipeline → unit test skeletons"
    ]
  }
}
```

---

## 7. Gaps

```json
{
  "missing": [
    {
      "gap": "angular_entries.json mangler route paths — alle er empty string",
      "impact": "Kan ikke auto-mappe Angular component → URL — kræver NAVIGATION_MODEL.json som fallback",
      "fix": "angular_analyzer.py skal parse route definitions med regex på 'path:' strings i routing modules"
    },
    {
      "gap": "messaging/030_flows.json = [WizardStep] — ingen strukturerede flows",
      "impact": "Messaging-domain (kerne-produktet) kan ikke generere E2E tests eller journeys automatisk",
      "fix": "Manuel enrichment af messaging-flows baseret på UI_MODEL_MESSAGE_WIZARD.json som kilde"
    },
    {
      "gap": "address_management — ingen flows, ingen behaviors (completeness=0.58)",
      "impact": "Adressevalg-trin i wizard (det vigtigste UI-trin) har nul coverage i pipeline",
      "fix": "Dedikeret domain enrichment pass for address_management"
    },
    {
      "gap": "Ingen data-testid registry — pipeline kender ikke selectors",
      "impact": "E2E test-generering kan give struktur men ikke fungerende assertions",
      "fix": "Byg data-testid-registry.json ved at scanne eksisterende E2E tests + Razor-filer"
    },
    {
      "gap": "ui_coverage_report.json er tom (menus: [])",
      "impact": "coverage_analyzer.py kører men producerer ingen nyttig output",
      "fix": "angular_analyzer.py → menu-extraction kræver parse af app.menu.component.ts"
    },
    {
      "gap": "Ingen journey schema — journeys er kun i denne doc, ikke structured JSON",
      "impact": "journey_to_demo pipeline kan ikke læse journeys automatisk",
      "fix": "Definer journey schema (se nedenfor, slice_C)"
    }
  ],

  "risks": [
    {
      "risk": "UI_MODEL_*.json er manuelt kurateret — kan blive forældet",
      "probability": "medium",
      "mitigation": "Bindende SSOT-regel: UI_MODEL opdateres ved ENHVER UI-ændring i green-ai"
    },
    {
      "risk": "identity_access er eneste high-quality domain — pipeline er afhængig af dette ene",
      "probability": "low (identity er stabilt)",
      "mitigation": "Enrichment prioritet: messaging (0.47) → address_management (0.58)"
    },
    {
      "risk": "Demo pipeline producerer MP4 men ikke business-validering",
      "probability": "certain",
      "mitigation": "Demo og E2E er separate pipelines — demo er presentation, ikke regression"
    }
  ],

  "assumptions": [
    "UI_MODEL_*.json er korrekte repræsentationer af sms-service Angular UI",
    "green-ai implementeres med Blazor Server (ikke reuse af Angular kode)",
    "data-testids i eksisterende grøn-ai tests er canonical og kan bruges som selector-kilde",
    "Azure TTS (da-DK-ChristelNeural) forbliver tilgængeligt for demo-generering"
  ]
}
```

---

## 8. Næste 5 Slices (konkrete, implementerbare)

```json
{
  "next_slices": [
    {
      "id": "PIPE_A",
      "name": "Data-TestId Registry",
      "goal": "Skab en maskinlæsbar registry over ALLE data-testid selectors i green-ai",
      "input": "tests/GreenAi.E2E/**/*.cs + src/GreenAi.Api/**/*.razor",
      "output": "analysis-tool/data/testid_registry.json — { selector: string, page: string, verified: bool }",
      "why": "Pipeline-blocker nr. 1 — ingen E2E-generering eller demo-mapping fungerer uden dette",
      "how": "PowerShell script: grep data-testid fra alle .cs + .razor filer → JSON",
      "complexity": "low",
      "duration_estimate": "1-2 timer"
    },
    {
      "id": "PIPE_B",
      "name": "Messaging Flow Enrichment",
      "goal": "Berig messaging/030_flows.json med strukturerede flows fra UI_MODEL_MESSAGE_WIZARD.json",
      "input": "docs/UI_MODEL_MESSAGE_WIZARD.json (5 nodes, 3 variants, state conditions)",
      "output": "domains/messaging/030_flows.json — 5+ FLOW_XXX entries med trigger, steps, branches",
      "why": "Messaging er kerne-produktet med completeness=0.47 — pipeline er blind uden dette",
      "how": "Manuel enrichment: konvertér UI_MODEL_MESSAGE_WIZARD flow-nodes til FLOW_XXX format",
      "complexity": "medium",
      "duration_estimate": "2-3 timer"
    },
    {
      "id": "PIPE_C",
      "name": "Journey Schema + Generator",
      "goal": "Definer journey JSON schema + byg JourneyBuilder der konverterer flows til journeys",
      "input": "domains/identity_access/030_flows.json + data/testid_registry.json (fra PIPE_A)",
      "output": "analysis-tool/data/journeys.json — structured journeys med persona, steps, selectors",
      "schema": {
        "journey": {
          "id": "string",
          "name": "string",
          "persona": "string",
          "source_flows": ["FLOW_001", "FLOW_005"],
          "steps": [
            {
              "step": 1,
              "description": "string",
              "url": "string",
              "action": "click | fill | wait",
              "selector": "data-testid string",
              "voice": "string (SSML narration)"
            }
          ]
        }
      },
      "why": "Eneste måde at gøre demo-generering reproducerbar og data-drevet",
      "complexity": "medium",
      "duration_estimate": "3-4 timer"
    },
    {
      "id": "PIPE_D",
      "name": "Flow-to-E2E Test Generator",
      "goal": "Python script der læser en FLOW_XXX entry og genererer Playwright test-skeleton (.cs)",
      "input": "domains/{domain}/030_flows.json + data/testid_registry.json",
      "output": "generated/{domain}/{flow_id}E2ETest_skeleton.cs",
      "template": "xUnit [Fact], base class E2ETestBase, LoginAndNavigateAsync + WaitForSelectorAsync + TODO markers for assertions",
      "example_output": {
        "flow": "FLOW_005 PasswordReset",
        "generates": "PasswordResetE2ETest.cs med: login, navigate /auth/reset-password, fill email, submit, assert success"
      },
      "why": "Fjerner manuel E2E test-skrivning for alle flows der har FLOW_XXX struktur",
      "complexity": "medium",
      "duration_estimate": "4-6 timer"
    },
    {
      "id": "PIPE_E",
      "name": "Demo Script Generator fra Journey",
      "goal": "Script der læser journeys.json → genererer Playwright DemoFlow test + voice script automatisk",
      "input": "analysis-tool/data/journeys.json (fra PIPE_C)",
      "output": "scripts/demo/generated/{journey_id}/DemoTest.cs + voice-script.txt",
      "mapping": "journey.step → HighlightAsync(selector) + ClickAsync + voice line per step",
      "why": "Gør det muligt at generere ny demo-video fra en ny journey UDEN manuel kode-skrivning",
      "dependency": "PIPE_A (testid_registry) + PIPE_C (journeys schema)",
      "complexity": "medium-high",
      "duration_estimate": "6-8 timer"
    }
  ]
}
```

---

## 9. Prioriteret rækkefølge

```
PIPE_A (testid registry)    ← blocker for alt andet — gør FØRST
PIPE_B (messaging flows)    ← parallel med A — ren skriveøvelse
PIPE_C (journey schema)     ← efter A
PIPE_D (flow→e2e generator) ← efter A + B
PIPE_E (demo generator)     ← efter A + C
```

Hele kæden er mulig **i dag** for identity_access domænet.  
For messaging (core product): mulig efter PIPE_B.  
For address_management: kræver separat enrichment pass (ikke i disse 5 slices).

---

## 10. Hvad der er UNKNOWN (Stop Rule)

```
UNKNOWN: angular_entries.json route paths — alle tomme
UNKNOWN: address_management flows — completeness 0.58, ingen FLOW_XXX entries
UNKNOWN: messaging behaviors — 020_behaviors.json er tom
UNKNOWN: wizard step 3-4 data-testids i green-ai
UNKNOWN: 2FA UI implementering plan i green-ai
UNKNOWN: Resend-dialog selector for demo journey 2
UNKNOWN: Email-mock strategy for PasswordReset E2E flow
```

---

*SSOT: `analysis-tool/docs/PIPELINE_ARCHITECTURE.md`*  
*Relateret: `docs/UI_MODEL_SCHEMA.json` | `docs/NAVIGATION_MODEL.json` | `PRODUCT_CAPABILITY_MAP.json`*
