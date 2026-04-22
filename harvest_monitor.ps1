param([int]$StartDone = 30)
# Ensure python alias is set to venv
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPy) { Set-Alias -Name python -Value $venvPy -Scope Script -Force }
$env:PYTHONIOENCODING = 'utf-8'
<#
  harvest_monitor.ps1
  - Runs sequential harvest 10 at a time (--resume, no reset)
  - After each batch: validate + emit, log counts to temp.md
  - STOP when flows >= 50 AND requirements >= 50
  - STOP if flows don't grow over 20 consecutive components (2 batches)
#>
$env:PYTHONIOENCODING = 'utf-8'
$python  = 'c:\Udvikling\analysis-tool\.venv\Scripts\python.exe'
$cwd     = 'c:\Udvikling\analysis-tool'
$tempmd  = Join-Path $cwd 'temp.md'
$corpus  = Join-Path $cwd 'corpus'
$harvest = Join-Path $cwd 'harvest'

function Get-Count($file) {
    $p = Join-Path $corpus $file
    if (-not (Test-Path $p)) { return 0 }
    (Get-Content $p -Encoding utf8 | Where-Object { $_ }).Count
}

function Get-DoneCount {
    $mpath = Join-Path $harvest 'harvest-manifest.json'
    if (-not (Test-Path $mpath)) { return 0 }
    $m = Get-Content $mpath -Encoding utf8 -Raw | ConvertFrom-Json
    ($m.PSObject.Properties.Value | Where-Object { $_.status -eq 'DONE' }).Count
}

$no_growth_batches = 0
$last_flows = Get-Count 'flows.jsonl'
$done_now   = Get-DoneCount
$batch_num  = 0

# Write header to temp.md
$header = @"

## HARVEST MONITOR -- $(Get-Date -Format 'yyyy-MM-ddTHH:mm')Z START

| Batch | Done | flows | reqs | ui_verified | ui_inferred | note |
|---|---|---|---|---|---|---|
"@
Add-Content -Path $tempmd -Encoding utf8 -Value $header

Write-Host "[START] done=$done_now  flows=$last_flows"

while ($true) {
    $batch_num++
    $target = $done_now + 10

    Write-Host "[Batch $batch_num] target=$target ..."

    # Run harvest (resume = skip reset)
    & $python (Join-Path $cwd 'scripts\harvest\run_sequential.py') --target $target --resume 2>&1 | Out-Null

    # Re-read done count
    $done_now = Get-DoneCount

    # Validate + emit
    & $python (Join-Path $cwd 'scripts\harvest\validate_llm_output.py') 2>&1 | Out-Null
    & $python (Join-Path $cwd 'scripts\harvest\emit_to_jsonl.py') 2>&1 | Out-Null

    # Count corpus
    $flows = Get-Count 'flows.jsonl'
    $reqs  = Get-Count 'requirements.jsonl'
    $uiv   = Get-Count 'ui_behaviors_verified.jsonl'
    $uii   = Get-Count 'ui_behaviors_inferred.jsonl'

    # Check no-growth
    if ($flows -eq $last_flows) { $no_growth_batches++ } else { $no_growth_batches = 0 }
    $last_flows = $flows

    $note = if ($no_growth_batches -ge 1) { "flows_stagnant x$no_growth_batches" } else { "" }

    Write-Host "[Batch $batch_num] done=$done_now flows=$flows reqs=$reqs uiv=$uiv uii=$uii $note"

    # Append row to temp.md
    $row = "| $batch_num | $done_now | $flows | $reqs | $uiv | $uii | $note |"
    Add-Content -Path $tempmd -Encoding utf8 -Value $row

    # STOP: threshold reached
    if ($flows -ge 50 -and $reqs -ge 50) {
        $msg = "`nSTOP: SIGNAL_THRESHOLD_REACHED flows=$flows reqs=$reqs"
        Add-Content -Path $tempmd -Encoding utf8 -Value $msg
        Write-Host $msg
        break
    }

    # STOP: no growth for 20 components (2 batches)
    if ($no_growth_batches -ge 2) {
        $msg = "`nSTOP: FLOWS_NOT_GROWING -- truth gate may be too aggressive. flows=$flows after $($done_now) components"
        Add-Content -Path $tempmd -Encoding utf8 -Value $msg
        Write-Host $msg
        break
    }
}

Write-Host "[DONE] Harvest monitor finished."
