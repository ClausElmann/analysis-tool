<#
.SYNOPSIS
    Validates an audit package ZIP against AUDIT_PACKAGE_PROTOCOL.md rules.

.DESCRIPTION
    Checks the ZIP for:
    - Both project roots present (analysis-tool, green-ai)
    - Required generated files present (PACKAGE_INDEX.md, PACKAGE_MANIFEST.json)
    - No forbidden binary/generated extensions
    - No forbidden folders (bin, obj, .git, etc.)
    - No runtime artifacts (.log, .jsonl, .map, .pre-partition)

.PARAMETER ZipPath
    Full path to the audit package ZIP. If omitted, uses the most recent ZIP in D:\Udvikling\audit-packages\

.EXAMPLE
    .\scripts\Validate-Audit-Package.ps1
    .\scripts\Validate-Audit-Package.ps1 -ZipPath "D:\Udvikling\audit-packages\audit-package-20260403-132037.zip"
#>
param(
    [string]$ZipPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression.FileSystem

# ─────────────────────────────────────────────────────────────
# RESOLVE ZIP
# ─────────────────────────────────────────────────────────────
if (-not $ZipPath) {
    $ZipPath = (Get-ChildItem "D:\Udvikling\audit-packages\*.zip" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1).FullName
    if (-not $ZipPath) {
        Write-Host "No ZIP found in D:\Udvikling\audit-packages\" -ForegroundColor Red
        exit 1
    }
    Write-Host "Auto-selected: $ZipPath"
}

if (-not (Test-Path $ZipPath)) {
    Write-Host "ZIP not found: $ZipPath" -ForegroundColor Red
    exit 1
}

# ─────────────────────────────────────────────────────────────
# RULES (must match AUDIT_PACKAGE_PROTOCOL.md)
# ─────────────────────────────────────────────────────────────
$ForbiddenExtensions = @(
    '.dll','.exe','.pdb','.lib','.so','.dylib',
    '.nupkg','.snupkg','.whl','.egg',
    '.zip','.tar','.gz','.rar','.7z',
    '.png','.jpg','.jpeg','.gif','.webp','.bmp','.ico','.svg',
    '.woff','.woff2','.ttf','.eot','.otf',
    '.pdf','.mp4','.mp3','.wav','.avi',
    '.db','.sqlite','.mdf','.ldf',
    '.cache','.suo','.dbmdl','.jfm','.bim',
    '.map',                   # CSS/JS source maps
    '.log','.jsonl',          # runtime logs
    '.pre-partition'          # analysis-tool partition state
)

$ForbiddenFolderPatterns = @(
    '(^|/)bin/',
    '(^|/)obj/',
    '(^|/)\.git/',
    '(^|/)\.vs/',
    '(^|/)node_modules/',
    '(^|/)__pycache__/',
    '(^|/)\.pytest_cache/',
    '(^|/)TestResults/',
    '(^|/)Screenshots/',
    '(^|/)\.venv/',
    '(^|/)venv/',
    '(^|/)\.idea/'
)

$RequiredFiles    = @('PACKAGE_INDEX.md', 'PACKAGE_MANIFEST.json')
$RequiredRoots    = @('analysis-tool/', 'green-ai/')

# UI audit: Visual folders where images are explicitly allowed
$UiAuditVisualPrefix    = 'green-ai/tests/GreenAi.E2E/TestResults/Visual/'
$UiAuditResultsPrefix   = 'green-ai/tests/GreenAi.E2E/TestResults/'
$VisualImageExts        = @('.png','.jpg','.jpeg','.gif','.webp','.bmp')

# System audit asset paths
$SysAuditSsotPrefix     = 'green-ai/docs/SSOT/'
$SysAuditGovPrefix      = 'analysis-tool/core/'
$SysAuditFrontendPrefix = 'green-ai/src/GreenAi.Api/Components/'
$SysAuditBackendPrefix  = 'green-ai/src/GreenAi.Api/Features/'
$SysAuditTestsPrefix    = 'green-ai/tests/GreenAi.Tests/'

# ─────────────────────────────────────────────────────────────
# LOAD ZIP
# ─────────────────────────────────────────────────────────────
$archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
$entries = @($archive.Entries)
$archive.Dispose()

Write-Host ""
Write-Host "Audit Package Validation" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host "Package : $(Split-Path $ZipPath -Leaf)"
Write-Host "Entries : $($entries.Count)"
Write-Host ""

$violations = @()
$checks     = 0

function Add-Violation($id, $message) {
    $script:violations += [PSCustomObject]@{ Id = $id; Message = $message }
}

# ─────────────────────────────────────────────────────────────
# CHECK 1: Required root folders
# ─────────────────────────────────────────────────────────────
foreach ($root in $RequiredRoots) {
    $checks++
    $found = $entries | Where-Object { $_.FullName -like "$root*" }
    if ($found.Count -eq 0) {
        Add-Violation "ROOT-001" "Required project root missing: $root"
    } else {
        Write-Host "  [ok] Root present: $root ($($found.Count) entries)"
    }
}

# ─────────────────────────────────────────────────────────────
# CHECK 2: Required files at ZIP root
# ─────────────────────────────────────────────────────────────
foreach ($req in $RequiredFiles) {
    $checks++
    $found = @($entries | Where-Object { $_.Name -eq $req -and $_.FullName -eq $req })
    if ($found.Count -eq 0) {
        Add-Violation "REQ-001" "Required file missing at ZIP root: $req"
    } else {
        Write-Host "  [ok] Required file: $req"
    }
}

# ─────────────────────────────────────────────────────────────
# CHECK 3: No forbidden extensions
# ─────────────────────────────────────────────────────────────
$checks++
$badExtFiles = @($entries | Where-Object {
    $ext      = [System.IO.Path]::GetExtension($_.Name).ToLower()
    if (-not ($ForbiddenExtensions -contains $ext)) { return $false }
    # Images are allowed inside Visual audit folders only
    $entryPath = $_.FullName.Replace('\', '/')
    if (($VisualImageExts -contains $ext) -and ($entryPath -like "$UiAuditVisualPrefix*")) { return $false }
    return $true
})
if ($badExtFiles.Count -gt 0) {
    foreach ($f in $badExtFiles) {
        Add-Violation "EXT-001" "Forbidden extension in package: $($f.FullName)"
    }
} else {
    Write-Host "  [ok] No forbidden extensions"
}

# ─────────────────────────────────────────────────────────────
# CHECK 4: No forbidden folders
# ─────────────────────────────────────────────────────────────
$checks++
$folderViolations = @()
foreach ($entry in $entries) {
    $entryPath = $entry.FullName.Replace('\', '/')
    # Entries under the explicitly allowed E2E TestResults path are exempt
    if ($entryPath -like "$UiAuditResultsPrefix*") { continue }
    foreach ($pattern in $ForbiddenFolderPatterns) {
        if ($entryPath -match $pattern) {
            $folderViolations += $entry.FullName
            break
        }
    }
}
if ($folderViolations.Count -gt 0) {
    foreach ($path in $folderViolations) {
        Add-Violation "FOLDER-001" "Entry inside forbidden folder: $path"
    }
} else {
    Write-Host "  [ok] No forbidden folders"
}

# ─────────────────────────────────────────────────────────────
# CHECK 5: E2E TestResults folder present
# ─────────────────────────────────────────────────────────────
$checks++
$testResultsEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "$UiAuditResultsPrefix*"
})
if ($testResultsEntries.Count -eq 0) {
    Add-Violation "UI-001" "TestResults folder missing: green-ai/tests/GreenAi.E2E/TestResults/ — run governance tests first"
} else {
    Write-Host "  [ok] TestResults present: $($testResultsEntries.Count) entr(ies)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 6: Screenshots present under Visual/current/
# ─────────────────────────────────────────────────────────────
$checks++
$visualCurrentPrefix = "$UiAuditVisualPrefix" + "current/"
$screenshotEntries = @($entries | Where-Object {
    $ext  = [System.IO.Path]::GetExtension($_.Name).ToLower()
    $path = $_.FullName.Replace('\', '/')
    ($VisualImageExts -contains $ext) -and ($path -like "$UiAuditVisualPrefix*")
})
if ($screenshotEntries.Count -eq 0) {
    Add-Violation "UI-002" "No screenshots under Visual/current/ — run visual E2E tests before packaging"
} else {
    Write-Host "  [ok] Screenshots: $($screenshotEntries.Count) file(s) in Visual/"
}

# ─────────────────────────────────────────────────────────────
# CHECK 7: CSS files present
# ─────────────────────────────────────────────────────────────
$checks++
$cssEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "green-ai/src/GreenAi.Api/wwwroot/css/*" -and
    $_.Name -match '\.css$'
})
if ($cssEntries.Count -eq 0) {
    Add-Violation "UI-003" "CSS files missing: green-ai/src/GreenAi.Api/wwwroot/css/ — required for design token audit"
} else {
    Write-Host "  [ok] CSS files: $($cssEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 8: UI SSOT docs present
# ─────────────────────────────────────────────────────────────
$checks++
$uiDocEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "green-ai/docs/SSOT/ui/*"
})
if ($uiDocEntries.Count -eq 0) {
    Add-Violation "UI-004" "UI SSOT docs missing: green-ai/docs/SSOT/ui/ — required for design system audit"
} else {
    Write-Host "  [ok] UI SSOT docs: $($uiDocEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 9: No images outside Visual folders
# ─────────────────────────────────────────────────────────────
$checks++
$allImageExts = @('.png','.jpg','.jpeg','.gif','.webp','.bmp','.ico','.svg')
$imagesOutsideVisual = @($entries | Where-Object {
    $ext  = [System.IO.Path]::GetExtension($_.Name).ToLower()
    $path = $_.FullName.Replace('\', '/')
    ($allImageExts -contains $ext) -and -not ($path -like "$UiAuditVisualPrefix*")
})
if ($imagesOutsideVisual.Count -gt 0) {
    foreach ($f in $imagesOutsideVisual) {
        Add-Violation "UI-005" "Image outside allowed Visual/ folder: $($f.FullName)"
    }
} else {
    Write-Host "  [ok] No images outside Visual/ folders"
}

# ─────────────────────────────────────────────────────────────
# CHECK 10: Full SSOT present (green-ai/docs/SSOT/)
# ─────────────────────────────────────────────────────────────
$checks++
$ssotEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "$SysAuditSsotPrefix*"
})
if ($ssotEntries.Count -eq 0) {
    Add-Violation "SYS-001" "Full SSOT missing: green-ai/docs/SSOT/ — required for architecture alignment audit"
} else {
    Write-Host "  [ok] Full SSOT: $($ssotEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 11: Governance tooling present (analysis-tool/core/)
# ─────────────────────────────────────────────────────────────
$checks++
$govEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "$SysAuditGovPrefix*"
})
if ($govEntries.Count -eq 0) {
    Add-Violation "SYS-002" "Governance tooling missing: analysis-tool/core/ — required for pipeline quality audit"
} else {
    Write-Host "  [ok] Governance tooling: $($govEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 12: Frontend source present (green-ai/src/GreenAi.Api/Components/)
# ─────────────────────────────────────────────────────────────
$checks++
$frontendEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "$SysAuditFrontendPrefix*"
})
if ($frontendEntries.Count -eq 0) {
    Add-Violation "SYS-003" "Frontend source missing: green-ai/src/GreenAi.Api/Components/ — required for UI audit"
} else {
    Write-Host "  [ok] Frontend source: $($frontendEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# CHECK 13: Backend source present (green-ai/src/GreenAi.Api/Features/)
# ─────────────────────────────────────────────────────────────
$checks++
$backendEntries = @($entries | Where-Object {
    $_.FullName.Replace('\', '/') -like "$SysAuditBackendPrefix*"
})
if ($backendEntries.Count -eq 0) {
    Add-Violation "SYS-004" "Backend source missing: green-ai/src/GreenAi.Api/Features/ — required for architecture audit"
} else {
    Write-Host "  [ok] Backend source: $($backendEntries.Count) file(s)"
}

# ─────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────
Write-Host ""
if ($violations.Count -eq 0) {
    Write-Host "All $checks checks passed. Package is valid." -ForegroundColor Green
    Write-Host ""
    Write-Host "Validation checklist:" -ForegroundColor Cyan
    Write-Host "  [x] Both project roots present"
    Write-Host "  [x] PACKAGE_INDEX.md and PACKAGE_MANIFEST.json present"
    Write-Host "  [x] No binary/generated file extensions"
    Write-Host "  [x] No bin/obj/.git/etc. folders"
    Write-Host "  [x] E2E TestResults folder included"
    Write-Host "  [x] Screenshots present (Visual/current/)"
    Write-Host "  [x] CSS files included"
    Write-Host "  [x] UI SSOT docs included"
    Write-Host "  [x] No images outside Visual/ folders"
    Write-Host "  [x] Full SSOT present"
    Write-Host "  [x] Governance tooling present"
    Write-Host "  [x] Frontend source present"
    Write-Host "  [x] Backend source present"
    exit 0
} else {
    Write-Host "$($violations.Count) violation(s) found:" -ForegroundColor Red
    $violations | ForEach-Object {
        Write-Host "  [$($_.Id)] $($_.Message)" -ForegroundColor Yellow
    }
    exit 1
}
