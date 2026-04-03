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
    $ext = [System.IO.Path]::GetExtension($_.Name).ToLower()
    $ForbiddenExtensions -contains $ext
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
    foreach ($pattern in $ForbiddenFolderPatterns) {
        if ($entry.FullName -match $pattern) {
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
    exit 0
} else {
    Write-Host "$($violations.Count) violation(s) found:" -ForegroundColor Red
    $violations | ForEach-Object {
        Write-Host "  [$($_.Id)] $($_.Message)" -ForegroundColor Yellow
    }
    exit 1
}
