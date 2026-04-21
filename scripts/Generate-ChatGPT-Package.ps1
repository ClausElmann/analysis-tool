# Generate-ChatGPT-Package.ps1
# Layer 1 (analysis-tool output) + Layer 2 (green-ai) + Layer 3 (governance tools: dfep_v3, dfep_v2, analysis_tool/idle)
param([string]$OutputPath = $null)

$timestamp   = Get-Date -Format "yyyyMMdd-HHmmss"
$pkgName     = "ChatGPT-Package"
$tmp         = Join-Path $env:TEMP "ChatGPT-Package-$timestamp"
$atRoot      = "c:\Udvikling\analysis-tool"
$gaRoot      = "c:\Udvikling\green-ai"

Write-Host "Generating Architect Review Package (Layer 1 + Layer 2)..." -ForegroundColor Cyan

if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

# --- helper: copy files excluding certain dirs and extensions ---
function Copy-Filtered {
    param($SrcRoot, $DestRoot, $ExcludeDirs, $ExcludeExts)
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
    Get-ChildItem -Path $SrcRoot -Recurse -File | Where-Object {
        $f = $_
        if ($ExcludeExts -contains $f.Extension.ToLower()) { return $false }
        if ($f.Name -eq 'analysetemp.md') { return $false }
        $parts = $f.FullName.Substring($SrcRoot.Length).Split([IO.Path]::DirectorySeparatorChar)
        foreach ($p in $parts) { if ($ExcludeDirs -contains $p) { return $false } }
        return $true
    } | ForEach-Object {
        $rel  = $_.FullName.Substring($SrcRoot.Length + 1)
        $dest = Join-Path $DestRoot $rel
        $dir  = Split-Path $dest -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $_.FullName $dest -Force
    }
    return (Get-ChildItem $DestRoot -Recurse -File).Count
}

# --- Layer 1: analysis-tool output ---
Write-Host "Layer 1: analysis-tool..."
$atExcludeDirs = @('raw','output','.venv','.git','.pytest_cache','__pycache__','tests',
                   'analyzers','core','utils','prompts','ui','bin','obj','.vs','temp_history')
$atExcludeExts = @('.py','.pyc','.log','.zip','.dll','.exe','.pdb','.suo','.user')
$atCount = Copy-Filtered $atRoot "$tmp\analysis-tool" $atExcludeDirs $atExcludeExts
Write-Host "   -> $atCount filer"

# --- Layer 4: Harvest scripts + output (eksplicit tracking) ---
Write-Host "Layer 4: harvest scripts + output..."
$harvestScriptCount = 0
$harvestOutputCount = 0
@('scripts\harvest', 'harvest') | ForEach-Object {
    $hSrc = Join-Path $atRoot $_
    if (Test-Path $hSrc) {
        Get-ChildItem -Path $hSrc -Recurse -File | Where-Object {
            $atExcludeExts -notcontains $_.Extension.ToLower()
        } | ForEach-Object {
            $rel  = $_.FullName.Substring($atRoot.Length + 1)
            $dest = Join-Path "$tmp\analysis-tool" $rel
            $d    = Split-Path $dest -Parent
            if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
            Copy-Item $_.FullName $dest -Force
            if ($rel -like 'scripts\harvest*') { $harvestScriptCount++ }
            else                              { $harvestOutputCount++ }
        }
    }
}
Write-Host "   -> scripts: $harvestScriptCount  output: $harvestOutputCount filer"

# --- Layer 3: governance tools (Python source - kun specifikke governance-moduler) ---
Write-Host "Layer 3: governance tools (dfep_v3, dfep_v2, analysis_tool/idle)..."
$govDirs = @('dfep_v3', 'dfep_v2', 'analysis_tool')
$govExcludeExts = @('.pyc','.log','.zip')
$govCount = 0
foreach ($dir in $govDirs) {
    $src = Join-Path $atRoot $dir
    if (Test-Path $src) {
        Get-ChildItem -Path $src -Recurse -File | Where-Object {
            $govExcludeExts -notcontains $_.Extension.ToLower()
        } | ForEach-Object {
            $rel  = $_.FullName.Substring($atRoot.Length + 1)
            $dest = Join-Path "$tmp\analysis-tool" $rel
            $d    = Split-Path $dest -Parent
            if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
            Copy-Item $_.FullName $dest -Force
            $govCount++
        }
    }
}
Write-Host "   -> $govCount filer"

# --- Layer 2: green-ai ---
Write-Host "Layer 2: green-ai..."
$gaExcludeDirs = @('bin','obj','.vs','.git','TestResults','.venv','__pycache__','node_modules')
$gaExcludeExts = @('.dll','.exe','.pdb','.zip','.nupkg','.suo','.user','.cache','.log','.dbmdl','.jfm')
$gaCount = Copy-Filtered $gaRoot "$tmp\green-ai" $gaExcludeDirs $gaExcludeExts
Write-Host "   -> $gaCount filer"

# --- Domain state (fra analysis-tool/domains/*/000_meta.json) ---
Write-Host "Generating domain state..."
Push-Location $atRoot
$domainMeta = Get-ChildItem "domains\*\000_meta.json" | ForEach-Object {
    try {
        $m = Get-Content $_.FullName -Raw | ConvertFrom-Json
        [PSCustomObject]@{ Domain=$m.domain; Score=$m.completeness_score; Gaps=$m.gaps_count; Status=$m.status }
    } catch {}
} | Where-Object { $_ } | Sort-Object Score -Descending
Pop-Location

$avg   = if ($domainMeta) { [math]::Round(($domainMeta | Measure-Object Score -Average).Average, 2) } else { 0 }
$high  = ($domainMeta | Where-Object Score -ge 0.90 | Measure-Object).Count
$med   = ($domainMeta | Where-Object { $_.Score -ge 0.75 -and $_.Score -lt 0.90 } | Measure-Object).Count
$low   = ($domainMeta | Where-Object Score -lt 0.75 | Measure-Object).Count

# --- STATE_SUMMARY.md ---
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# ARCHITECT PACKAGE - STATE SUMMARY")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("> ⚠️ **SNAPSHOT ONLY** — Not operational truth.")
[void]$sb.AppendLine("> For live operational state, use **GREEN_AI_BUILD_STATE.md** + **analysis-tool/temp.md**.")
[void]$sb.AppendLine("> This file may be stale relative to the active session.")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## PACKAGE INDHOLD")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| Layer | Repo | Filer |")
[void]$sb.AppendLine("|-------|------|-------|")
[void]$sb.AppendLine("| Layer 1 | analysis-tool (ekstraheret viden) | $atCount |")
[void]$sb.AppendLine("| Layer 2 | green-ai (implementering) | $gaCount |")
[void]$sb.AppendLine("| Layer 3 | governance tools (dfep_v3, dfep_v2, idle harvest) | $govCount |")
[void]$sb.AppendLine("| Layer 4 | harvest scripts + output (Start-AutonomousHarvest.ps1, *.jsonl) | $($harvestScriptCount + $harvestOutputCount) |")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## DOMAIN ANALYSE STATUS")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| Metric | Vaerdi |")
[void]$sb.AppendLine("|--------|--------|")
[void]$sb.AppendLine("| Total domaener | $($domainMeta.Count) |")
[void]$sb.AppendLine("| Gennemsnit | $avg |")
[void]$sb.AppendLine("| Hoj >=0.90 | $high |")
[void]$sb.AppendLine("| Medium 0.75-0.89 | $med |")
[void]$sb.AppendLine("| Lav <0.75 | $low |")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## KLAR TIL DESIGN (>=0.85)")
[void]$sb.AppendLine("")
$domainMeta | Where-Object Score -ge 0.85 | ForEach-Object {
    [void]$sb.AppendLine("- **$($_.Domain)**: $($_.Score) ($($_.Gaps) gaps)")
}

[void]$sb.AppendLine("")
[void]$sb.AppendLine("## SCORES MANGLER (000_meta.json tom eller ingen score-felt)")
[void]$sb.AppendLine("")
$domainMeta | Where-Object { $null -eq $_.Score -or $_.Score -eq '' } | ForEach-Object {
    [void]$sb.AppendLine("- **$($_.Domain)**: MANGLER SCORE — kør analyse igen")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## MANGLER MERE OUTPUT FRA ANALYSIS-TOOL (<0.75)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("> Bed analysis-tool om dybere analyse -- derefter ny ZIP")
[void]$sb.AppendLine("")
$domainMeta | Where-Object Score -lt 0.75 | ForEach-Object {
    [void]$sb.AppendLine("- **$($_.Domain)**: $($_.Score) ($($_.Gaps) gaps)")
}
$sb.ToString() | Out-File "$tmp\STATE_SUMMARY.md" -Encoding UTF8

# --- DOMAIN_OVERVIEW.md ---
$ov = [System.Text.StringBuilder]::new()
[void]$ov.AppendLine("# DOMAIN OVERVIEW -- $($domainMeta.Count) domaener")
[void]$ov.AppendLine("")
[void]$ov.AppendLine("| Domain | Score | Gaps | Status |")
[void]$ov.AppendLine("|--------|-------|------|--------|")
$domainMeta | ForEach-Object {
    $s = if ($_.Score -ge 0.85) { "READY" } elseif ($_.Score -ge 0.75) { "minor gaps" } else { "BERIG OUTPUT" }
    [void]$ov.AppendLine("| $($_.Domain) | $($_.Score) | $($_.Gaps) | $s |")
}
$ov.ToString() | Out-File "$tmp\DOMAIN_OVERVIEW.md" -Encoding UTF8

# --- README.md ---
$rm = [System.Text.StringBuilder]::new()
[void]$rm.AppendLine("# START HERE -- Architect Review Package")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("> **PROOF OF READ — PACKAGE_TOKEN: PLACEHOLDER_TOKEN**")
[void]$rm.AppendLine("> Dit svar SKAL starte med dette token som bevis paa at du har aabnet denne fil.")
[void]$rm.AppendLine("> Svar baseret paa chat-historik (ikke ZIP) accepteres IKKE.")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("**Dato:** $(Get-Date -Format 'yyyy-MM-dd HH:mm') | **Til:** ChatGPT Architect")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("## HURTIG START")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("1. Laes STATE_SUMMARY.md -- hvad er klar, hvad mangler")
[void]$rm.AppendLine("2. Laes DOMAIN_OVERVIEW.md -- alle $($domainMeta.Count) domaener pa et blik")
[void]$rm.AppendLine("3. Browse analysis-tool/domains/{domain}/ -- detaljerede udtraek")
[void]$rm.AppendLine("4. Browse analysis-tool/analysis/ -- 22 LOCKED wave-filer (DLR, contracts, system-status)")
[void]$rm.AppendLine("5. Browse green-ai/ -- nuvaerende byggetilstand")
[void]$rm.AppendLine("6. Laes analysis-tool/docs/ARCHITECT_ONBOARDING.md -- samarbejdsregler og workflows")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("## PAKKE STRUKTUR")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("| Mappe | Layer | Indhold |")
[void]$rm.AppendLine("|-------|-------|---------|")
[void]$rm.AppendLine("| analysis-tool/domains/ | L1 | $($domainMeta.Count) domaener x 10 artefakttyper |")
[void]$rm.AppendLine("| analysis-tool/analysis/ | L1 | 22 LOCKED wave-filer |")
[void]$rm.AppendLine("| analysis-tool/ai-slices/ | L1 | Slice-specs pr domae |")
[void]$rm.AppendLine("| analysis-tool/data/ | L1 | Pipeline-output: db_schema, api_map, bg_services |")
[void]$rm.AppendLine("| analysis-tool/docs/ | L1 | SSOT model, decisions, plans |")
[void]$rm.AppendLine("| analysis-tool/ai-governance/ | L1 | Builder-Architect protokol + governance |")
[void]$rm.AppendLine("| green-ai/src/ | L2 | Feature slices + DB migrations |")
[void]$rm.AppendLine("| green-ai/docs/ | L2 | SSOT, ARCHITECTURE, DECISIONS |")
[void]$rm.AppendLine("| green-ai/ai-governance/ | L2 | 13 governance-filer |")
[void]$rm.AppendLine("| analysis-tool/docs/GREEN_AI_BUILD_STATE.md | L1/L2 | Build state, tech, locks, domain states |")
[void]$rm.AppendLine("| green-ai/AI_WORK_CONTRACT.md | L2 | Trigger-tabel + absolutte regler |")
[void]$rm.AppendLine("| analysis-tool/dfep_v3/ | L3 | DFEP v3 Copilot-native engine (Python source) |")
[void]$rm.AppendLine("| analysis-tool/dfep_v2/ | L3 | DFEP v2 hybrid engine (Python source) |")
[void]$rm.AppendLine("| analysis-tool/analysis_tool/idle/ | L3 | Idle Harvest v1 loop (Python source) |")
[void]$rm.AppendLine("| analysis-tool/scripts/harvest/ | L4 | Harvest script (Start-AutonomousHarvest.ps1) |")
[void]$rm.AppendLine("| analysis-tool/harvest/angular/normalized/ | L4 | behaviors.jsonl + flows.jsonl + requirements.jsonl |")
[void]$rm.AppendLine("| analysis-tool/harvest/component-list.json | L4 | Sampled component paths (de 10 analyserede) |")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("## HVAD ER EKSKLUDERET (Layer 0)")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("- sms-service kildekode (C# + SQL + Razor)")
[void]$rm.AppendLine("- WIKI dokumentation")
[void]$rm.AppendLine("- raw/ data (PDF, CSV, labels.json)")
[void]$rm.AppendLine("- Python implementering (*.py scripts) — UNDTAGEN governance-moduler (dfep_v3, dfep_v2, analysis_tool/idle)")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("## WORKFLOW")
[void]$rm.AppendLine("")
[void]$rm.AppendLine("Mangler arkitekten info -> bed analysis-tool om at producere bedre output -> ny ZIP")
$rm.ToString() | Out-File "$tmp\README.md" -Encoding UTF8

# --- Layer 2.5: Visual Intelligence ---
Write-Host "Layer 2.5: visual intelligence..."
$viDest = "$tmp\analysis-tool\visual-intelligence"
$viPython = Join-Path $atRoot ".venv\Scripts\python.exe"
$viRegistry = Join-Path $atRoot "data\visual_validation_registry.jsonl"
if (Test-Path $viPython) {
    Push-Location $atRoot
    $viOut = & $viPython -m core.visual_intelligence_reporter `
        --registry $viRegistry `
        --output-dir $viDest 2>&1
    Pop-Location
    Write-Host "   -> $viOut"
} else {
    # Fallback: lav tomme placeholder-filer hvis venv ikke tilgængelig
    New-Item -ItemType Directory -Path "$viDest\stats" -Force | Out-Null
    '[]' | Out-File "$viDest\cache_index.jsonl" -Encoding UTF8
    '{"note":"venv not found — run Generate-ChatGPT-Package.ps1 from analysis-tool with venv active"}' | Out-File "$viDest\stats\component_stability.json" -Encoding UTF8
    '{"note":"venv not found"}' | Out-File "$viDest\stats\failure_patterns.json" -Encoding UTF8
    Write-Host "   -> placeholder (venv not found)"
}

# --- ZIP ---
Write-Host "Creating ZIP..."
$zipPath = if ($OutputPath) { $OutputPath } else { Join-Path $atRoot "ChatGPT-Package.zip" }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

# --- PACKAGE_TOKEN: skriv til temp.md ---
# Format: GA-YYYY-MMDD-V{migration}-{HHmm}
# Henter migration level direkte fra green-ai migrations-mappe (altid korrekt)
$migrationsPath = Join-Path $gaRoot "src\GreenAi.Api\Database\Migrations"
$migrationLevel = "V???"
if (Test-Path $migrationsPath) {
    $highest = Get-ChildItem $migrationsPath -Filter "V*.sql" |
        ForEach-Object { if ($_.BaseName -match '^(V\d+)') { $Matches[1] } } |
        Sort-Object { [int]($_ -replace 'V','') } |
        Select-Object -Last 1
    if ($highest) { $migrationLevel = $highest }
}
$tokenDate    = Get-Date -Format "yyyy-MMdd"
$tokenTime    = Get-Date -Format "HHmm"
$packageToken = "GA-$tokenDate-$migrationLevel-$tokenTime"

# --- Opdater README.md i tmp med korrekt token (PLACEHOLDER_TOKEN → rigtig token) ---
$readmePath = "$tmp\README.md"
if (Test-Path $readmePath) {
    (Get-Content $readmePath -Raw) -replace 'PLACEHOLDER_TOKEN', $packageToken | Set-Content $readmePath -Encoding UTF8 -NoNewline
}

# --- Opdater temp.md på disk med token OG kopier ind i $tmp FØR compress ---
$tempMdPath = Join-Path $atRoot "temp.md"
if (Test-Path $tempMdPath) {
    $tempContent = Get-Content $tempMdPath -Raw
    # Fjern ALLE eksisterende scattered token-blokke (inkl. V??? varianter)
    $tempContent = $tempContent -replace '(?m)^> \*\*PACKAGE_TOKEN: GA-[\w?-]+\*\*\r?\n> ChatGPT SKAL.*?\r?\n> Svar der.*?\r?\n(\r?\n)?', ''
    # Opdater token-citation inde i audit-prompten
    $tempContent = $tempContent -replace '"PACKAGE_TOKEN: GA-[\w?-]+ bekræftet\."', """PACKAGE_TOKEN: $packageToken bekræftet."""
    # Global erstatning: ALLE token-forekomster i filen (historiske rapporter, etc.)
    $tempContent = $tempContent -replace 'GA-\d{4}-\d{4}-V\d{3}-\d{4}', $packageToken
    # Sæt ét canonical token-block præcist efter FØRSTE --- separator (max 1 indsætning)
    $tokenBlock = "> **PACKAGE_TOKEN: $packageToken**`n> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.`n> Svar der IKKE starter med token-citering afvises.`n`n"
    $rxSep = [regex]::new('(?m)^---\s*\r?\n')
    $tempContent = $rxSep.Replace($tempContent, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Value + $tokenBlock }, 1)
    Set-Content -Path $tempMdPath -Value $tempContent -Encoding UTF8 -NoNewline
    Write-Host "PACKAGE_TOKEN: $packageToken  →  temp.md opdateret" -ForegroundColor Yellow

    # Kopier opdateret temp.md ind i ZIP-arbejdsmappen (INDEN compress)
    $tempMdDest = "$tmp\analysis-tool\temp.md"
    $tempMdDestDir = Split-Path $tempMdDest -Parent
    if (-not (Test-Path $tempMdDestDir)) { New-Item -ItemType Directory -Path $tempMdDestDir -Force | Out-Null }
    Copy-Item $tempMdPath $tempMdDest -Force
}

# --- Compress ---
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$tmp\*" -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item $tmp -Recurse -Force

$sz = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "DONE" -ForegroundColor Green
Write-Host $zipPath -ForegroundColor Cyan
Write-Host "Stoerrelse: $sz MB | L1: $atCount filer | L2: $gaCount filer | L3 (governance): $govCount filer"
