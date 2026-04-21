# ============================================
# HARVEST BOOTSTRAP SCRIPT
# ============================================

$root = "C:/Udvikling/sms-service/ServiceAlert.Web/ClientApp"
$outputFolder = "C:/Udvikling/analysis-tool/harvest"

$componentListPath = "$outputFolder/component-list.json"
$manifestPath = "$outputFolder/harvest-manifest.json"

Write-Host "Scanning for Angular components..."

$files = Get-ChildItem -Path $root -Recurse -Filter *.component.ts | Sort-Object FullName

# -----------------------------
# BUILD COMPONENT LIST (DISCOVERY)
# -----------------------------
$componentList = @()

foreach ($file in $files) {
    $rel = $file.FullName.Substring($root.Length + 1).Replace("\", "/")

    $name = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $componentName = $name -replace "\.component$", ""

    $componentList += [PSCustomObject]@{
        name = $componentName
        path = $rel
    }
}

# Fjern duplicates (path)
$componentList = $componentList | Sort-Object path -Unique

# Save component-list.json
$componentList | ConvertTo-Json -Depth 4 | Set-Content $componentListPath -Encoding UTF8

Write-Host "component-list.json generated: $($componentList.Count) components"

# -----------------------------

# BUILD HARVEST MANIFEST (DICT FORMAT)
# -----------------------------
$manifest = @{}
foreach ($comp in $componentList) {
    $manifest[$comp.path] = @{
        component     = $comp.name
        path          = $comp.path
        status        = "PENDING"
        lastProcessed = $null
    }
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content $manifestPath -Encoding UTF8

Write-Host "harvest-manifest.json generated: $($manifest.Count) entries"

# -----------------------------
# DEBUG OUTPUT
# -----------------------------
Write-Host ""
Write-Host "First 5 components:"
$componentList | Select-Object -First 5 | ForEach-Object {
    Write-Host "- $($_.name)"
}