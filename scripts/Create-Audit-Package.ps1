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
  "totalFileCount": $totalCount
}
"@

Set-Content -Path (Join-Path $StagingRoot "PACKAGE_MANIFEST.json") -Value $manifest -Encoding UTF8

# ---------------------------------------------------------------------------
# GENERATE PACKAGE_INDEX.md
# ---------------------------------------------------------------------------
function Get-FolderTree {
    param([string]$Path, [int]$MaxDepth = 2, [int]$CurrentDepth = 0, [string]$Indent = "")
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

# Key files
$keyPatterns = @("README*", "*.sln", "*.slnx", "DECISIONS*", "ARCHITECTURE*", "CODE-REVIEW*", "AUDIT*", "AGENTS*", "PROMPT_HEADER*")
$keyFiles = @()
foreach ($root in $copiedRoots) {
    $rootPath = Join-Path $StagingRoot $root
    foreach ($pattern in $keyPatterns) {
        $found = Get-ChildItem -Path $rootPath -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($f in $found) {
            $rel = $f.FullName.Substring($StagingRoot.Length).TrimStart('\', '/')
            $keyFiles += "- $rel"
        }
    }
    # ai-governance files
    $govPath = Join-Path $rootPath "ai-governance"
    if (Test-Path $govPath) {
        $govFiles = Get-ChildItem -Path $govPath -File
        foreach ($f in $govFiles) {
            $rel = $f.FullName.Substring($StagingRoot.Length).TrimStart('\', '/')
            $keyFiles += "- $rel"
        }
    }
}
$keyFilesText = ($keyFiles | Sort-Object -Unique) -join "`n"

$excludedSummary = "Folders: $($ExcludedFolders -join ', ')  |  Extensions: $($ExcludedExtensions -join ', ')"

$index = @"
# Audit Package Index

**Package:** $PackageName.zip
**Created:** $TimestampIso (UTC)
**Total files:** $totalCount

---

## Included Projects

$(($copiedRoots | ForEach-Object { "- $_" }) -join "`n")

---

## Excluded Patterns

$excludedSummary

---

## Top-Level Folder Tree

``````
$treeText
``````

---

## Key Files

$keyFilesText

---

## File Count by Extension

$(($countByExt.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "- ``$($_.Key)`` : $($_.Value)" }) -join "`n")
"@

Set-Content -Path (Join-Path $StagingRoot "PACKAGE_INDEX.md") -Value $index -Encoding UTF8

# ---------------------------------------------------------------------------
# CREATE ZIP
# ---------------------------------------------------------------------------
Write-Host "Creating ZIP: $ZipPath"
Compress-Archive -Path "$StagingRoot\*" -DestinationPath $ZipPath -CompressionLevel Optimal

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
