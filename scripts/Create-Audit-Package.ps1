<#
.SYNOPSIS
    Creates a combined audit package ZIP of analysis-tool and green-ai for external review.

.DESCRIPTION
    Copies source files from both projects into a staging folder, excludes binary/generated content,
    generates PACKAGE_INDEX.md and PACKAGE_MANIFEST.json, then ZIPs to a predictable output location.
    This is an AUDIT package — not a deployment, not a backup.

.PARAMETER OutputDir
    Directory where the ZIP will be written. Defaults to D:\Udvikling\audit-packages\

.EXAMPLE
    & "C:\Udvikling\analysis-tool\scripts\Create-Audit-Package.ps1"
    & "C:\Udvikling\analysis-tool\scripts\Create-Audit-Package.ps1" -OutputDir "D:\MyAudits"
#>
param(
    [string]$OutputDir = "D:\Udvikling\audit-packages"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these if project roots move
# ---------------------------------------------------------------------------
$ProjectRoots = @(
    "C:\Udvikling\analysis-tool",
    "C:\Udvikling\green-ai"
)

$ExcludedFolders = @(
    "bin", "obj", ".vs", ".git", "node_modules",
    "__pycache__", ".pytest_cache", "TestResults",
    "Screenshots", ".venv", "venv", ".idea",
    "output", "raw"
)

$ExcludedExtensions = @(
    ".dll", ".exe", ".pdb", ".lib", ".so", ".dylib",
    ".nupkg", ".snupkg", ".whl", ".egg",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".mp4", ".mp3", ".wav", ".avi",
    ".db", ".sqlite", ".mdf", ".ldf",
    ".cache", ".suo", ".dbmdl", ".jfm", ".bim",
    ".map",                        # CSS/JS source maps — generated, no review value
    ".log", ".jsonl",             # runtime engine output — transient, not source
    ".pre-partition"               # analysis-tool internal data partition files
)

# ---------------------------------------------------------------------------
# VALIDATE PROJECT ROOTS
# ---------------------------------------------------------------------------
foreach ($root in $ProjectRoots) {
    if (-not (Test-Path $root)) {
        Write-Error "Project root not found: $root — aborting."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------
$Timestamp     = Get-Date -Format "yyyyMMdd-HHmmss"
$TimestampIso  = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$PackageName   = "audit-package-$Timestamp"
$StagingRoot   = Join-Path $env:TEMP $PackageName
$ZipPath       = Join-Path $OutputDir "$PackageName.zip"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
    Write-Host "Created output directory: $OutputDir"
}

if (Test-Path $StagingRoot) {
    Remove-Item $StagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingRoot | Out-Null
Write-Host "Staging folder: $StagingRoot"

# ---------------------------------------------------------------------------
# COPY FUNCTION — excludes binary/transient content
# ---------------------------------------------------------------------------
function Copy-SourceTree {
    param(
        [string]$SourceRoot,
        [string]$DestRoot
    )

    $allFiles = Get-ChildItem -Path $SourceRoot -Recurse -File

    foreach ($file in $allFiles) {
        $relativePath = $file.FullName.Substring($SourceRoot.Length).TrimStart('\', '/')

        # Check if any path segment is an excluded folder
        $segments = $relativePath -split '[/\\]'
        $inExcludedFolder = $false
        foreach ($segment in $segments[0..($segments.Count - 2)]) {
            if ($ExcludedFolders -contains $segment) {
                $inExcludedFolder = $true
                break
            }
        }
        if ($inExcludedFolder) { continue }

        # Check file extension
        if ($ExcludedExtensions -contains $file.Extension.ToLower()) { continue }

        $destPath = Join-Path $DestRoot $relativePath
        $destDir  = Split-Path $destPath -Parent

        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir | Out-Null
        }

        try {
            Copy-Item -Path $file.FullName -Destination $destPath -ErrorAction Stop
        } catch {
            Write-Warning "Skipped (locked or inaccessible): $($file.FullName)"
        }
    }
}

# ---------------------------------------------------------------------------
# COPY PROJECTS
# ---------------------------------------------------------------------------
$copiedRoots = @()
foreach ($root in $ProjectRoots) {
    $folderName = Split-Path $root -Leaf
    $dest       = Join-Path $StagingRoot $folderName
    Write-Host "Copying $folderName ..."
    Copy-SourceTree -SourceRoot $root -DestRoot $dest
    $copiedRoots += $folderName
}

# ---------------------------------------------------------------------------
# UI AUDIT ASSETS — green-ai E2E screenshots + test results (additive)
# Images are allowed only inside Visual/ subfolders per protocol UI extensions.
# ---------------------------------------------------------------------------
$GreenAiRoot      = "C:\Udvikling\green-ai"
$GreenAiStageDest = Join-Path $StagingRoot "green-ai"
$E2EResultsRoot   = Join-Path $GreenAiRoot "tests\GreenAi.E2E\TestResults"

$VisualImageExts  = @('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
$screenshotCount  = 0

# ---------------------------------------------------------------------------
# SCREENSHOT FRESHNESS CHECK
# Screenshots are STALE if: folder missing, no images, newest > 24h old, or
# any source .cs/.razor/.css changed after the newest screenshot.
# ---------------------------------------------------------------------------
$VisualCurrentPath    = Join-Path $E2EResultsRoot "Visual\current"
$StalenessThresholdH  = 24   # hours
$screenshotFreshnessStatus = "MISSING"
$screenshotLastGenerated   = "n/a"
$screenshotIsStale         = $true

if (Test-Path $VisualCurrentPath) {
    $imageFiles = @(Get-ChildItem -Path $VisualCurrentPath -Recurse -File |
                   Where-Object { $VisualImageExts -contains $_.Extension.ToLower() })

    if ($imageFiles.Count -eq 0) {
        $screenshotFreshnessStatus = "EMPTY"
    } else {
        $newestImage   = $imageFiles | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
        $ageHours      = [math]::Round(((Get-Date).ToUniversalTime() - $newestImage.LastWriteTimeUtc).TotalHours, 1)
        $screenshotLastGenerated = $newestImage.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mmZ") + " (${ageHours}h ago)"

        if ($ageHours -gt $StalenessThresholdH) {
            $screenshotFreshnessStatus = "STALE (${ageHours}h old)"
        } else {
            # Check for source changes after newest screenshot
            $GreenAiSrcPath = Join-Path $GreenAiRoot "src"
            $GreenAiCssPath = Join-Path $GreenAiRoot "src\GreenAi.Api\wwwroot\css"
            $sourceChangedAfter = $false
            foreach ($srcDir in @($GreenAiSrcPath)) {
                if (-not (Test-Path $srcDir)) { continue }
                $newerSrc = Get-ChildItem -Path $srcDir -Recurse -File -Include "*.cs","*.razor","*.css" -ErrorAction SilentlyContinue |
                            Where-Object { $_.LastWriteTimeUtc -gt $newestImage.LastWriteTimeUtc } |
                            Select-Object -First 1
                if ($newerSrc) {
                    $sourceChangedAfter = $true
                    $screenshotFreshnessStatus = "STALE (source changed: $($newerSrc.Name))"
                    break
                }
            }
            if (-not $sourceChangedAfter) {
                $screenshotFreshnessStatus = "FRESH"
                $screenshotIsStale = $false
            }
        }
    }
}

if ($screenshotIsStale) {
    Write-Host ""
    Write-Host "  [WARNING] Visual screenshots are stale or missing." -ForegroundColor Yellow
    Write-Host "  Status  : $screenshotFreshnessStatus" -ForegroundColor Yellow
    Write-Host "  The UI audit will have limited visual evidence." -ForegroundColor Yellow
    Write-Host "  To regenerate, run:" -ForegroundColor Yellow
    Write-Host "    dotnet test tests/GreenAi.E2E --filter 'FullyQualifiedName~Visual' --nologo" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "  Screenshots: $screenshotFreshnessStatus — $screenshotLastGenerated"
}

# ── 1. Visual screenshot folders (images allowed) ──────────────────────────
$visualFolders = @(
    [PSCustomObject]@{ Src = Join-Path $E2EResultsRoot "Visual\current";  Required = $true  },
    [PSCustomObject]@{ Src = Join-Path $E2EResultsRoot "Visual\baseline"; Required = $false }
)

foreach ($vf in $visualFolders) {
    if (-not (Test-Path $vf.Src)) {
        if ($vf.Required) { Write-Warning "UI Audit: Visual/current not found: $($vf.Src)" }
        continue
    }
    $relFromGreenAi = $vf.Src.Substring($GreenAiRoot.Length).TrimStart('\', '/')
    $destVisual     = Join-Path $GreenAiStageDest $relFromGreenAi
    $vfFiles        = Get-ChildItem -Path $vf.Src -Recurse -File
    foreach ($file in $vfFiles) {
        $relFile  = $file.FullName.Substring($vf.Src.Length).TrimStart('\', '/')
        $destFile = Join-Path $destVisual $relFile
        $destDir  = Split-Path $destFile -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        try {
            Copy-Item -Path $file.FullName -Destination $destFile -ErrorAction Stop
            if ($VisualImageExts -contains $file.Extension.ToLower()) { $screenshotCount++ }
        } catch {
            Write-Warning "UI Audit: Skipped: $($file.FullName)"
        }
    }
    $leafName = Split-Path $vf.Src -Leaf
    Write-Host "  UI Audit: Visual/$leafName — $screenshotCount screenshot(s)"
}

# ── 2. TestResults non-image files (trx, xml — no binaries, no images) ────
if (Test-Path $E2EResultsRoot) {
    $trxFiles = Get-ChildItem -Path $E2EResultsRoot -Recurse -File |
                Where-Object {
                    $ext = $_.Extension.ToLower()
                    ($ExcludedExtensions -notcontains $ext) -and
                    ($VisualImageExts    -notcontains $ext) -and
                    ($_.FullName -notlike "*\Visual\*")    # Visual already copied above
                }
    foreach ($file in $trxFiles) {
        $relFile  = $file.FullName.Substring($GreenAiRoot.Length).TrimStart('\', '/')
        $destFile = Join-Path $GreenAiStageDest $relFile
        $destDir  = Split-Path $destFile -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        try { Copy-Item -Path $file.FullName -Destination $destFile -ErrorAction Stop } catch {
            Write-Warning "UI Audit: Skipped TRX: $($file.FullName)"
        }
    }
    Write-Host "  UI Audit: TestResults non-image files included"
}

# ── 3. Verify presence of docs/CSS (already copied by main tree) ───────────
$uiDocsPresent = Test-Path (Join-Path $GreenAiStageDest "docs\SSOT\ui")
$cssPresent    = Test-Path (Join-Path $GreenAiStageDest "src\GreenAi.Api\wwwroot\css")
Write-Host "  UI Audit: UI SSOT docs present: $uiDocsPresent | CSS present: $cssPresent"

# ---------------------------------------------------------------------------
# SYSTEM AUDIT — presence verification (assets already copied by main tree)
# ---------------------------------------------------------------------------
$AnalysisToolDest  = Join-Path $StagingRoot "analysis-tool"

$ssotPath          = Join-Path $GreenAiStageDest "docs\SSOT"
$ssotPresent       = Test-Path $ssotPath
$ssotFileCount     = if ($ssotPresent) {
                         (Get-ChildItem -Path $ssotPath -Recurse -File -ErrorAction SilentlyContinue).Count
                     } else { 0 }

$govToolingPresent = Test-Path (Join-Path $AnalysisToolDest "core")
$frontendPresent   = Test-Path (Join-Path $GreenAiStageDest "src\GreenAi.Api\Components")
$backendPresent    = Test-Path (Join-Path $GreenAiStageDest "src\GreenAi.Api\Features")
$testsPresent      = Test-Path (Join-Path $GreenAiStageDest "tests\GreenAi.Tests")

Write-Host "  System Audit: SSOT present: $ssotPresent ($ssotFileCount files) | Governance tooling: $govToolingPresent"
Write-Host "  System Audit: Frontend: $frontendPresent | Backend: $backendPresent | Tests: $testsPresent"

# ---------------------------------------------------------------------------
# COLLECT STATS FOR MANIFEST
# ---------------------------------------------------------------------------
$allStagedFiles = Get-ChildItem -Path $StagingRoot -Recurse -File
$totalCount     = $allStagedFiles.Count

$countByExt = @{}
foreach ($f in $allStagedFiles) {
    $ext = if ($f.Extension) { $f.Extension.ToLower() } else { "(no extension)" }
    if ($countByExt.ContainsKey($ext)) {
        $countByExt[$ext]++
    } else {
        $countByExt[$ext] = 1
    }
}

# ---------------------------------------------------------------------------
# GENERATE PACKAGE_MANIFEST.json
# ---------------------------------------------------------------------------
$extJson = ($countByExt.GetEnumerator() | Sort-Object Name | ForEach-Object {
    "    `"$($_.Key)`": $($_.Value)"
}) -join ",`n"

$rootsJson = ($copiedRoots | ForEach-Object { "    `"$_`"" }) -join ",`n"

$excludedFoldersJson = ($ExcludedFolders | ForEach-Object { "    `"$_`"" }) -join ",`n"
$excludedExtJson     = ($ExcludedExtensions | ForEach-Object { "    `"$_`"" }) -join ",`n"

$manifest = @"
{
  "packageName": "$PackageName.zip",
  "timestamp": "$TimestampIso",
  "includedRoots": [
$rootsJson
  ],
  "excludedFolders": [
$excludedFoldersJson
  ],
  "excludedExtensions": [
$excludedExtJson
  ],
  "fileCountByExtension": {
$extJson
  },
  "totalFileCount": $totalCount,
  "uiAudit": {
    "screenshotsIncluded": $(if ($screenshotCount -gt 0) { "true" } else { "false" }),
    "screenshotCount": $screenshotCount,
    "cssFilesIncluded": $(if ($cssPresent) { "true" } else { "false" }),
    "uiDocsIncluded": $(if ($uiDocsPresent) { "true" } else { "false" })
  },
  "systemAudit": {
    "ui": {
      "screenshotsIncluded": $(if ($screenshotCount -gt 0) { "true" } else { "false" }),
      "screenshotCount": $screenshotCount
    },
    "ssot": {
      "present": $(if ($ssotPresent) { "true" } else { "false" }),
      "filesCount": $ssotFileCount
    },
    "frontend": $(if ($frontendPresent) { "true" } else { "false" }),
    "backend": $(if ($backendPresent) { "true" } else { "false" }),
    "governance": $(if ($govToolingPresent) { "true" } else { "false" }),
    "tests": $(if ($testsPresent) { "true" } else { "false" })
  }
}
"@

Set-Content -Path (Join-Path $StagingRoot "PACKAGE_MANIFEST.json") -Value $manifest -Encoding UTF8

# ---------------------------------------------------------------------------
# GENERATE PACKAGE_INDEX.md — AI navigation guide
# ---------------------------------------------------------------------------

# Pre-compute screenshot warning line for use inside here-string
$screenshotWarningLine = if ($screenshotIsStale -or $screenshotCount -eq 0) {
    "`n> **WARNING: No valid visual evidence included — UI audit will be limited.**  `n> Run: ``dotnet test tests/GreenAi.E2E --filter 'FullyQualifiedName~Visual' --nologo``"
} else { "" }

# Detect screenshot device folders (desktop/tablet/mobile etc.)
$deviceFolders = @()
$visualCurrentStagePath = Join-Path $GreenAiStageDest "tests\GreenAi.E2E\TestResults\Visual\current"
if (Test-Path $visualCurrentStagePath) {
    $deviceFolders = @(Get-ChildItem -Path $visualCurrentStagePath -Directory | Select-Object -ExpandProperty Name)
}
$deviceSummary = if ($deviceFolders.Count -gt 0) { $deviceFolders -join ', ' } else { "unknown" }

# Detect key SSOT files
$ssotKeyFiles = @()
if ($ssotPresent) {
    $ssotKeyFiles = @(Get-ChildItem -Path (Join-Path $GreenAiStageDest "docs\SSOT") -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "_*" } |
        Sort-Object Name |
        Select-Object -First 20 |
        ForEach-Object { "  - " + $_.FullName.Substring($GreenAiStageDest.Length).TrimStart('\', '/') })
}
$ssotKeyFilesText = if ($ssotKeyFiles.Count -gt 0) { $ssotKeyFiles -join "`n" } else { "  (not found)" }

# Build compact tree (depth 3)
function Get-FolderTree {
    param([string]$Path, [int]$MaxDepth = 3, [int]$CurrentDepth = 0, [string]$Indent = "")
    if ($CurrentDepth -ge $MaxDepth) { return }
    $items = Get-ChildItem -Path $Path | Sort-Object { $_.PSIsContainer } -Descending | Sort-Object Name
    foreach ($item in $items) {
        if ($item.PSIsContainer) {
            if ($ExcludedFolders -contains $item.Name) { continue }
            "$Indent$($item.Name)/"
            Get-FolderTree -Path $item.FullName -MaxDepth $MaxDepth -CurrentDepth ($CurrentDepth + 1) -Indent "$Indent  "
        } else {
            "$Indent$($item.Name)"
        }
    }
}

$treeLines = @()
foreach ($root in $copiedRoots) {
    $treeLines += "$root/"
    $rootPath = Join-Path $StagingRoot $root
    $treeLines += Get-FolderTree -Path $rootPath -MaxDepth 2 -Indent "  "
    $treeLines += ""
}
$treeText = $treeLines -join "`n"

# Resolve actual relative paths for key entry points (present if file exists)
function Resolve-EntryPoint {
    param([string]$RelPath, [string]$Base)
    $full = Join-Path $Base $RelPath.Replace('/', '\')
    if (Test-Path $full) { "- ``$RelPath``" } else { "- ``$RelPath`` *(not found)*" }
}

$src = Join-Path $GreenAiStageDest "src\GreenAi.Api"

$index = @"
# PACKAGE INDEX — Green AI System Audit

---

## 1. SYSTEM OVERVIEW

- **System:** GreenAI — SMS/email broadcasting platform
- **Architecture:** Blazor Server + MediatR + Dapper (NO EF Core, NO ASP.NET Identity)
- **Multi-tenant:** Yes — CustomerId/ProfileId on every query
- **Auth:** Custom JWT — ICurrentUser, BlazorPrincipalHolder
- **UI:** MudBlazor 8 + design token system (--color-*, --font-*, --space-*) + 9 governance tests
- **Key constraint:** Zero compiler warnings required; all CSS values must use tokens

---

## 2. WHAT THIS PACKAGE IS FOR (AI INSTRUCTIONS)

This package is optimized for full-system enterprise audit:

- UI/UX consistency and design system validation
- SSOT / RED THREAD architecture alignment
- Governance enforcement coverage gaps
- Frontend + backend architecture quality
- Performance and enterprise readiness

**AI: do NOT summarize. Focus on:**
- Inconsistencies between SSOT docs and actual code
- Missing or incomplete governance enforcement
- UX issues (flows, empty states, error handling, loading states)
- Performance risks (render frequency, large lists, missing @key)
- Enterprise readiness gaps (accessibility, multi-tenant safety, error boundaries)

**Return: actionable findings, prioritized by impact.**

---

## 3. HIGH-LEVEL STRUCTURE

``````
$treeText
``````

---

## 4. CRITICAL ENTRY POINTS — START HERE

### Design System
$(Resolve-EntryPoint "src/GreenAi.Api/wwwroot/css/design-tokens.css" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/wwwroot/css/portal-skin.css" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/wwwroot/css/greenai-enterprise.css" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/wwwroot/css/greenai-skin.css" $GreenAiStageDest)

### SSOT — UI System
$(Resolve-EntryPoint "docs/SSOT/ui/color-system.md" $GreenAiStageDest)
$(Resolve-EntryPoint "docs/SSOT/ui/component-system.md" $GreenAiStageDest)
$(Resolve-EntryPoint "docs/SSOT/ui/patterns/mudblazor-conventions.md" $GreenAiStageDest)
$(Resolve-EntryPoint "docs/SSOT/ui/patterns/blazor-component-pattern.md" $GreenAiStageDest)

### Layouts
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Layout/MainLayout.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Layout/WizardLayout.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Layout/OverlayNav.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Layout/TopBar.razor" $GreenAiStageDest)

### Key UI Pages
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Broadcasting/BroadcastingHubPage.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Broadcasting/StatusPage.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Broadcasting/SendWizardPage.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Broadcasting/DraftsPage.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/CustomerAdmin/Index.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Auth/SelectCustomerPage.razor" $GreenAiStageDest)
$(Resolve-EntryPoint "src/GreenAi.Api/Components/Pages/Auth/SelectProfilePage.razor" $GreenAiStageDest)

### Governance Tests
$(Resolve-EntryPoint "tests/GreenAi.E2E/Governance/CssTokenComplianceTests.cs" $GreenAiStageDest)

### AI Governance
$(Resolve-EntryPoint "ai-governance/00_SYSTEM_RULES.json" $GreenAiStageDest)
$(Resolve-EntryPoint "ai-governance/04_ANTI_PATTERNS.json" $GreenAiStageDest)
$(Resolve-EntryPoint "AI_WORK_CONTRACT.md" $GreenAiStageDest)
$(Resolve-EntryPoint "AI_STATE.md" $GreenAiStageDest)

---

## 5. VISUAL EVIDENCE

- **Screenshots:** $screenshotCount file(s)
- **Freshness:** $screenshotFreshnessStatus
- **Last generated:** $screenshotLastGenerated
- **Devices covered:** $deviceSummary
- **Location:** ``green-ai/tests/GreenAi.E2E/TestResults/Visual/current/``
- **Baseline:** ``green-ai/tests/GreenAi.E2E/TestResults/Visual/baseline/`` (if present)
$screenshotWarningLine

Cross-reference screenshots with entry point pages to validate visual consistency.

---

## 6. SSOT / RED THREAD SUMMARY

SSOT files ($ssotFileCount total in ``green-ai/docs/SSOT/``):
$ssotKeyFilesText

Key authorities:
- ``docs/SSOT/ui/color-system.md`` — semantic color token roles (blue=actions, red=errors ONLY)
- ``docs/SSOT/ui/component-system.md`` — 15+ ``.ga-*`` utility classes replacing banned ``Style=`` attributes
- ``docs/SSOT/backend/patterns/`` — endpoint/handler/pipeline patterns
- ``docs/SSOT/identity/README.md`` — custom JWT, ICurrentUser, tenant isolation
- ``analysis-tool/ai-governance/`` — AI operating rules and anti-patterns

---

## 7. GOVERNANCE SUMMARY

**Hard-enforced (9 tests in CssTokenComplianceTests.cs — CI blocking):**
- No hardcoded hex/rgb() in CSS files
- No hardcoded font-size in portal-skin.css
- All ``<MudTable>`` must have ``Dense="true"``
- Banned inline ``Style=`` patterns (specific list)
- Plain ``<button>`` without ``.ga-btn-*`` class
- ``outline: none`` without focus replacement (WCAG)
- 22 required typography/spacing tokens in design-tokens.css

**Advisory (non-blocking):**
- ``MudButton Color.Error`` logged to console — allowed but flagged

**Intentionally flexible:**
- Font-size in CSS files other than portal-skin.css
- Spacing in Razor files beyond specific banned patterns
- MudDataGrid configuration details

---

## 8. KNOWN LIMITATIONS

- **Mock data:** Broadcasting, scenarios, drafts, addresses use ``MockData`` static class — no real API calls
- **Partial backend:** Some features (CreateUser, CreateProfile) return Snackbar info instead of real handler
- **Governance scope gap:** ``RazorFiles_DoNotContainBannedInlineStyles`` scans ``Components/`` only — ``Pages/`` and ``Features/`` Razor files are NOT scanned

---

## 9. INSTRUCTIONS FOR AI (MANDATORY)

When analyzing this package:

1. **Cross-check SSOT vs implementation** — find where code drifts from documented patterns
2. **Find governance gaps** — what should be enforced but isn't
3. **Identify UX issues** — missing loading states, empty states, error handling, accessibility
4. **Flag performance risks** — unnecessary renders, missing ``@key``, large list handling
5. **Report enterprise readiness** — multi-tenant safety, error boundaries, focus management

**Do NOT:**
- Summarize code that is already self-evident
- Describe folder structure (already in §3)
- Restate SSOT rules without finding violations

**Return: prioritized findings with file + line references where possible.**

---

## 10. PACKAGE METADATA

- **Package:** $PackageName.zip
- **Created:** $TimestampIso (UTC)
- **Total files:** $totalCount
- **Roots:** $(($copiedRoots) -join ', ')
- **System audit:** SSOT $ssotFileCount files | Screenshots $screenshotCount | CSS $(if ($cssPresent) { 'present' } else { 'MISSING' }) | Frontend $(if ($frontendPresent) { 'present' } else { 'MISSING' }) | Backend $(if ($backendPresent) { 'present' } else { 'MISSING' })
"@

Set-Content -Path (Join-Path $StagingRoot "PACKAGE_INDEX.md") -Value $index -Encoding UTF8

# ---------------------------------------------------------------------------
# CREATE ZIP — use .NET ZipFile directly; Compress-Archive wildcard expansion
# silently creates a 0-byte archive when the staging folder is large
# ---------------------------------------------------------------------------
Write-Host "Creating ZIP: $ZipPath"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $StagingRoot,
    $ZipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false   # includeBaseDirectory = false → staging folder itself not nested
)

# ---------------------------------------------------------------------------
# CLEANUP STAGING
# ---------------------------------------------------------------------------
Remove-Item $StagingRoot -Recurse -Force

# ---------------------------------------------------------------------------
# DONE
# ---------------------------------------------------------------------------
$zipSize = [math]::Round((Get-Item $ZipPath).Length / 1KB, 1)
Write-Host ""
Write-Host "Audit package created successfully."
Write-Host "  Output : $ZipPath"
Write-Host "  Size   : $zipSize KB"
Write-Host "  Files  : $totalCount"
Write-Host ""
Write-Host "Validation checklist:"
Write-Host "  [x] Both project roots included"
Write-Host "  [x] Binary/generated files excluded"
Write-Host "  [x] PACKAGE_INDEX.md generated"
Write-Host "  [x] PACKAGE_MANIFEST.json generated"
Write-Host "  [x] ZIP filename: $PackageName.zip"
Write-Host ""
Write-Host "UI Audit:"
Write-Host "  $(if ($screenshotCount -gt 0) { '[x]' } else { '[ ]' }) Screenshots: $screenshotCount file(s)"
Write-Host "  $(if ($cssPresent)    { '[x]' } else { '[ ]' }) CSS files included"
Write-Host "  $(if ($uiDocsPresent) { '[x]' } else { '[ ]' }) UI SSOT docs included"
Write-Host ""
Write-Host "System Audit:"
Write-Host "  $(if ($ssotPresent)        { '[x]' } else { '[ ]' }) Full SSOT present ($ssotFileCount files)"
Write-Host "  $(if ($govToolingPresent) { '[x]' } else { '[ ]' }) Governance tooling (analysis-tool/core)"
Write-Host "  $(if ($frontendPresent)   { '[x]' } else { '[ ]' }) Frontend source (Components/)"
Write-Host "  $(if ($backendPresent)    { '[x]' } else { '[ ]' }) Backend source (Features/)"
Write-Host "  $(if ($testsPresent)      { '[x]' } else { '[ ]' }) Tests (GreenAi.Tests/)"
