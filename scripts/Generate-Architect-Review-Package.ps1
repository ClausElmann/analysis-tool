# Generate-Architect-Review-Package.ps1
# Generate ZIP package for ChatGPT (Architect) review
# Contains ONLY extracted analysis-tool data (Layer 1), NOT original sms-service code (Layer 0)

param(
    [string]$OutputPath = "ARCHITECT_REVIEW_PACKAGE.zip"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "ARCHITECT_REVIEW_PACKAGE_$timestamp"
$tempFolder = Join-Path $env:TEMP $packageName

Write-Host "🔧 Generating Architect Review Package..." -ForegroundColor Cyan
Write-Host ""

# 1. Create temp folder
Write-Host "📁 Creating temporary folder: $tempFolder"
if (Test-Path $tempFolder) {
    Remove-Item $tempFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $tempFolder -Force | Out-Null

# 2. Copy protocol files
Write-Host "📋 Copying protocol files..."
Copy-Item "PROTOCOL_REVIEW_FOR_CHATGPT.md" "$tempFolder\" -Force
Copy-Item "ai-governance\AI_BUILDER_ARCHITECT_PROTOCOL.md" "$tempFolder\" -Force
Copy-Item "BUILDER_ARCHITECT_CHEAT_SHEET.md" "$tempFolder\" -Force
Copy-Item "temp.md" "$tempFolder\" -Force

# 3. Copy domain extractions (Layer 1 ONLY - exclude _archive/)
Write-Host "📊 Copying domain extractions (38 domains)..."
$domains = Get-ChildItem "domains" -Directory -Exclude "_archive"
foreach ($domain in $domains) {
    Copy-Item $domain.FullName "$tempFolder\domains\$($domain.Name)" -Recurse -Force
}

# 4. Generate state summary
Write-Host "📈 Generating state summary..."
$domainMeta = Get-ChildItem "domains\*\000_meta.json" | ForEach-Object {
    $meta = Get-Content $_.FullName | ConvertFrom-Json
    [PSCustomObject]@{
        Domain = $meta.domain
        Completeness = $meta.completeness_score
        Status = $meta.status
        Gaps = $meta.gaps_count
    }
} | Sort-Object -Property Completeness -Descending

$avgCompleteness = [math]::Round(($domainMeta | Measure-Object -Property Completeness -Average).Average, 2)
$highCount = ($domainMeta | Where-Object Completeness -ge 0.90).Count
$mediumCount = ($domainMeta | Where-Object {$_.Completeness -ge 0.75 -and $_.Completeness -lt 0.90}).Count
$lowCount = ($domainMeta | Where-Object Completeness -lt 0.75).Count

$summary = @"
# CURRENT STATE — $(Get-Date -Format "yyyy-MM-dd HH:mm")

## DOMAIN EXTRACTION STATUS

**Total Domains:** $($domainMeta.Count)

**Completeness Distribution:**
- ✅ High (≥0.90): $highCount domains — **Ready for green-ai design**
- ⚠️ Medium (0.75-0.89): $mediumCount domains — Minor gaps
- ❌ Low (<0.75): $lowCount domains — **Need analysis before green-ai**

**Average Completeness:** $avgCompleteness

---

## TOP DOMAINS (Ready for green-ai Design ≥0.85)

$($domainMeta | Where-Object Completeness -ge 0.85 | ForEach-Object { 
    "- **$($_.Domain)**: $($_.Completeness) completeness, $($_.Gaps) gap(s)" 
} | Out-String)

---

## DOMAINS NEEDING ANALYSIS (<0.75)

$($domainMeta | Where-Object Completeness -lt 0.75 | Select-Object -First 15 | ForEach-Object { 
    "- **$($_.Domain)**: $($_.Completeness) completeness, $($_.Gaps) gap(s) — ❌ **Request analysis**" 
} | Out-String)

---

## WHAT THIS PACKAGE CONTAINS

✅ **Extracted Domain Knowledge (Layer 1 - analysis-tool)**
   - $($domainMeta.Count) domains with completeness scores
   - Entities, behaviors, flows, integrations, business rules
   - Metadata: sources, gaps, iteration count, completeness scores

✅ **State Metrics**
   - Completeness distribution
   - Top domains ready for green-ai implementation
   - Domains requiring additional analysis

✅ **Protocol Documentation**
   - Builder-Architect workflow (Proposal-Driven)
   - Communication format (temp.md template)
   - Copilot analysis capabilities (6 types)

---

## WHAT IS EXCLUDED (By Design)

❌ **Original sms-service codebase (Layer 0)**
   - ServiceAlert.Core/*.cs (467+ entity files)
   - ServiceAlert.Services/*.cs (business logic)
   - ServiceAlert.Web/*.razor (UI components)
   - Database/*.sql (503+ migration files)

❌ **WIKI documentation** (Layer 0)
   - DEVELOPMENT/*.md files
   - Background service docs
   - Implementation guides

❌ **Raw data** (Layer 0)
   - PDFs (user manuals)
   - CSVs (data dumps)
   - labels.json (localization)

❌ **Python implementation**
   - *.py scripts (pipeline engines)
   - .venv/ (virtual environment)
   - output/ (pipeline artifacts)

---

## WHY LAYER 0 IS EXCLUDED

**Principle:** You design green-ai based on **CONCEPTS** (what sms-service does), NOT implementation (how sms-service does it).

**Workflow:**
1. Review extracted domains → Identify gaps
2. Request Copilot to analyze specific areas
3. Copilot scans Layer 0 → Extracts to Layer 1
4. New package generated with updated knowledge
5. Review → Design green-ai based on facts

**If you need more information:** Request Copilot to analyze → Copilot updates extraction → Repeat

---

## NEXT STEPS

1. **Read:** README.md (start here)
2. **Review:** ARCHITECT_DOMAIN_OVERVIEW.md (all domains at a glance)
3. **Browse:** domains/ folder (detailed extractions)
4. **Decide:** Which domains to prioritize for green-ai
5. **Request:** Copilot analysis for gaps/missing information

---

**Package Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Copilot (Builder):** analysis-tool extraction engine  
**ChatGPT (Architect):** green-ai strategic designer
"@

$summary | Out-File "$tempFolder\ARCHITECT_CURRENT_STATE.md" -Encoding UTF8

# 5. Generate domain overview
Write-Host "🗂️  Generating domain overview table..."
$overview = @"
# DOMAIN OVERVIEW

## All Domains ($($domainMeta.Count) total)

| Domain | Completeness | Status | Gaps | Ready? |
|--------|--------------|--------|------|--------|
$($domainMeta | ForEach-Object {
    $ready = if ($_.Completeness -ge 0.85) { "✅ YES" } elseif ($_.Completeness -ge 0.75) { "⚠️ Minor gaps" } else { "❌ Need analysis" }
    "| $($_.Domain) | $($_.Completeness) | $($_.Status) | $($_.Gaps) | $ready |"
} | Out-String)

---

## LEGEND

- **✅ YES:** Domain ready for green-ai DB design (completeness ≥ 0.85)
- **⚠️ Minor gaps:** Close to ready (0.75-0.84) - minor analysis needed
- **❌ Need analysis:** Request Copilot to extract more information (<0.75)

---

## HOW TO REQUEST ANALYSIS

**If domain has low completeness or gaps:**

\`\`\`
Example: messaging domain has 0.47 completeness

You: "Copilot: Analyze messaging domain from sms-service - extract tables, entities, and integration patterns"

Copilot: Scans sms-service → Extracts → Updates analysis-tool → Reports findings

You: Review findings → Accept/Reject/Request more
\`\`\`

---

**Package Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$overview | Out-File "$tempFolder\ARCHITECT_DOMAIN_OVERVIEW.md" -Encoding UTF8

# 6. Copy key documentation
Write-Host "📖 Copying documentation..."
New-Item -ItemType Directory -Path "$tempFolder\docs" -Force | Out-Null
Copy-Item "docs\SSOT_AUTHORITY_MODEL.md" "$tempFolder\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item ".github\copilot-instructions.md" "$tempFolder\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item "docs\ARCHITECT_REVIEW_PACKAGE_PROTOCOL.md" "$tempFolder\docs\" -Force -ErrorAction SilentlyContinue

# 7. Create README for ChatGPT (START HERE)
Write-Host "📝 Creating package README..."
$readme = @"
# 🎯 START HERE — Architect Review Package

**Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**For:** ChatGPT (Architect)  
**From:** Copilot (Builder)  
**Purpose:** Review extracted sms-service knowledge → Design green-ai

---

## 📋 QUICK START

1. **Read this file first** ← You are here
2. **Review:** ARCHITECT_CURRENT_STATE.md (domain extraction status)
3. **Browse:** ARCHITECT_DOMAIN_OVERVIEW.md (all $($domainMeta.Count) domains at a glance)
4. **Explore:** domains/ folder (detailed extractions)
5. **Read:** PROTOCOL_REVIEW_FOR_CHATGPT.md (workflow rules)

---

## 🔴 CRITICAL: WHAT YOU HAVE vs WHAT YOU DON'T

### ✅ YOU HAVE (Layer 1 - Extracted Knowledge)

**Extracted Domains:** $($domainMeta.Count) domains
- ✅ Entities (data models extracted from code)
- ✅ Behaviors (methods, operations)
- ✅ Flows (user journeys)
- ✅ Integrations (external dependencies: SendGrid, Twilio, etc.)
- ✅ Business rules (validation, constraints)
- ✅ Completeness scores (0.0-1.0)
- ✅ Gaps identified (what's missing)

**Example domain structure:**
\`\`\`
domains/Email/
  000_meta.json           ← Completeness: 0.91, Gaps: 1
  010_entities.json       ← EmailMessage, EmailTemplate, etc.
  020_behaviors.json      ← SendEmail, QueueEmail, RetryFailed
  030_flows.json          ← User sends email → Queue → Send → Log
  040_events.json         ← EmailSent, EmailFailed events
  050_batch.json          ← Background service patterns, retry logic
  060_integrations.json   ← SendGrid API integration
  070_rules.json          ← Validation rules (max recipients, subject length)
  080_pseudocode.json     ← Implementation sketches
  090_rebuild.json        ← Rebuilding notes for green-ai
  095_decision_support.json ← Design decisions
\`\`\`

### ❌ YOU DON'T HAVE (Layer 0 - Original Sources)

**Original sms-service codebase:**
- ❌ ServiceAlert.Core/*.cs (467+ C# entity files)
- ❌ ServiceAlert.Services/*.cs (business logic implementation)
- ❌ ServiceAlert.Web/*.razor (UI components)
- ❌ Database/*.sql (503+ SQL migration files)

**WIKI documentation:**
- ❌ DEVELOPMENT/*.md (background services, patterns)

**Raw data:**
- ❌ PDFs (user manuals)
- ❌ CSVs (data dumps)
- ❌ labels.json (localization strings)

**Python implementation:**
- ❌ *.py (extraction scripts)
- ❌ .venv/ (virtual environment)

---

## 🎯 WHY THIS SEPARATION?

**Principle:** You design green-ai based on **CONCEPTS** (requirements), NOT by copying sms-service implementation.

**You see:**
- ✅ WHAT sms-service does (business requirements)
- ✅ WHAT data exists (entities, relationships)
- ✅ WHAT flows exist (user journeys)

**You don't see:**
- ❌ HOW sms-service implements it (code specifics)
- ❌ Legacy patterns to avoid copying

**If you need more:** Request Copilot to analyze → Copilot extracts concepts → Updates domains

---

## 🤝 WORKFLOW: PROPOSAL-DRIVEN

### 1. You (Architect) give high-level goal
\`\`\`
Example: "Prepare Email domain for green-ai DB design"
\`\`\`

### 2. Copilot analyzes + proposes solution
\`\`\`
Copilot:
  • Scans original sms-service code (you don't have access)
  • Extracts tables, entities, patterns
  • Formulates CONCRETE PROPOSAL
  • Updates temp.md with findings + proposal
\`\`\`

### 3. You review proposal
\`\`\`
Options:
  ✅ ACCEPT: "Proceed with proposal"
  ❌ REJECT: "Alternative approach: [different strategy]"
  🔄 REQUEST MORE: "Analyze retry logic additionally"
\`\`\`

### 4. Copilot executes approved proposal
\`\`\`
Copilot:
  • Implements approved plan
  • Updates analysis-tool domains
  • Generates new package (if needed)
  • Reports completion
  • Proposes next step
\`\`\`

### 5. Loop until domain ready for green-ai

---

## 📊 CURRENT STATE SUMMARY

**Total Domains:** $($domainMeta.Count)
**Average Completeness:** $avgCompleteness

**Ready for green-ai (≥0.85):**
$($domainMeta | Where-Object Completeness -ge 0.85 | Measure-Object | Select-Object -ExpandProperty Count) domains

**Need analysis (<0.75):**
$($domainMeta | Where-Object Completeness -lt 0.75 | Measure-Object | Select-Object -ExpandProperty Count) domains

**See ARCHITECT_CURRENT_STATE.md for full breakdown**

---

## 📂 PACKAGE CONTENTS

\`\`\`
README.md                            ← YOU ARE HERE (start here!)
PROTOCOL_REVIEW_FOR_CHATGPT.md       ← Workflow protocol
AI_BUILDER_ARCHITECT_PROTOCOL.md     ← Full protocol (400+ lines)
BUILDER_ARCHITECT_CHEAT_SHEET.md     ← Quick reference
temp.md                              ← Current session state
ARCHITECT_CURRENT_STATE.md           ← Metrics & completeness
ARCHITECT_DOMAIN_OVERVIEW.md         ← All domains table
domains/                             ← $($domainMeta.Count) extracted domains
docs/SSOT_AUTHORITY_MODEL.md         ← 3-layer authority model
docs/copilot-instructions.md         ← Copilot role definition
docs/ARCHITECT_REVIEW_PACKAGE_PROTOCOL.md ← This package protocol
\`\`\`

---

## 🚀 READY TO START?

1. **Review state:** ARCHITECT_CURRENT_STATE.md
2. **Browse domains:** ARCHITECT_DOMAIN_OVERVIEW.md
3. **Pick priority:** Which domain to implement first in green-ai?
4. **Give directive:** High-level goal for Copilot
5. **Review proposal:** Copilot responds with concrete plan
6. **Approve/Reject:** Guide strategic direction

---

## 💡 EXAMPLE EXCHANGE

\`\`\`
You: "Review Email domain - is it ready for green-ai DB design?"

You read: domains/Email/000_meta.json (0.91 completeness, 1 gap)
You read: domains/Email/010_entities.json (EmailMessage, EmailTemplate, EmailQueue)
You read: domains/Email/050_batch.json (retry policy mentioned, sparse details)

You decide: "Need retry details before DB design"

You: "Copilot: Analyze Email retry logic - extract exact retry counts, delays, failure handling"

Copilot analyzes: sms-service/ServiceAlert.Services/Email/EmailBackgroundService.cs
Copilot extracts: 3 attempts, exponential backoff (1s/5s/15s), dead-letter queue after failure
Copilot updates: domains/Email/050_batch.json with detailed retry config (completeness → 0.93)
Copilot reports: "Email retry policy extracted - ready for green-ai DB design"

You review: Updated extraction sufficient

You: "ACCEPT - Design green-ai Email schema with retry metadata table"

You design: Green-ai Email DB schema based on extracted requirements
\`\`\`

---

**Ready? Start with ARCHITECT_CURRENT_STATE.md** 🚀
"@

$readme | Out-File "$tempFolder\README.md" -Encoding UTF8

# 8. Create ZIP
Write-Host "📦 Creating ZIP archive..."
$finalZipPath = Join-Path (Get-Location) "$packageName.zip"
if (Test-Path $finalZipPath) {
    Remove-Item $finalZipPath -Force
}

Compress-Archive -Path "$tempFolder\*" -DestinationPath $finalZipPath -CompressionLevel Optimal

# 9. Cleanup
Write-Host "🧹 Cleaning up temporary folder..."
Remove-Item $tempFolder -Recurse -Force

# 10. Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ ARCHITECT REVIEW PACKAGE CREATED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📦 Package:" -ForegroundColor Cyan
Write-Host "   $finalZipPath"
Write-Host ""
Write-Host "📊 Contains:" -ForegroundColor Cyan
Write-Host "   - $($domainMeta.Count) extracted domains (Layer 1 only)"
Write-Host "   - Protocol documentation (workflow rules)"
Write-Host "   - State metrics (completeness: $avgCompleteness avg)"
Write-Host "   - Domain overview table"
Write-Host ""
Write-Host "🚫 Excludes (by design):" -ForegroundColor Yellow
Write-Host "   - Original sms-service codebase (Layer 0)"
Write-Host "   - WIKI files"
Write-Host "   - Raw data (PDFs, CSVs)"
Write-Host "   - Python implementation"
Write-Host ""
Write-Host "✅ Ready for green-ai design:" -ForegroundColor Green
Write-Host "   - $highCount domains (completeness ≥ 0.90)"
Write-Host ""
Write-Host "⚠️  Need analysis:" -ForegroundColor Yellow
Write-Host "   - $lowCount domains (completeness < 0.75)"
Write-Host ""
Write-Host "📤 NEXT STEP:" -ForegroundColor Cyan
Write-Host "   Upload $packageName.zip to ChatGPT"
Write-Host "   ChatGPT starts with README.md"
Write-Host ""
