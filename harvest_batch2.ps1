param([string[]]$Domains = @("delivery","web_messages","standard_receivers","sms_group"), [int]$MaxCycles = 5)

Set-Location c:\Udvikling\analysis-tool
$path = "c:\Udvikling\analysis-tool\domains\domain_state.json"
$py = ".venv\Scripts\python.exe"

foreach ($domain in $Domains) {
    Write-Host "`n========== $domain ==========" -ForegroundColor Cyan
    $j = Get-Content $path -Raw | ConvertFrom-Json
    $pre_score = $j.$domain.completeness_score
    $pre_status = $j.$domain.status
    Write-Host "PRE: score=$pre_score status=$pre_status"

    for ($i = 1; $i -le $MaxCycles; $i++) {
        # Use Python for state modification (preserves all JSON fields)
        & $py set_domain_active.py $domain

        Write-Host "--- Cycle $i ---"
        & $py run_domain_engine.py --seeds $domain --once

        $j2 = Get-Content $path -Raw | ConvertFrom-Json
        $st = $j2.$domain.status
        $sc = $j2.$domain.completeness_score
        Write-Host "POST: score=$sc status=$st"

        if ($st -eq "complete") {
            Write-Host "DONE: $domain reached complete" -ForegroundColor Green
            break
        }
    }
}

Write-Host "`n=== FINAL STATE ===" -ForegroundColor Yellow
$j = Get-Content $path -Raw | ConvertFrom-Json
foreach ($d in @("delivery","web_messages","standard_receivers","sms_group")) {
    $sc = $j.$d.completeness_score
    $st = $j.$d.status
    Write-Host "$d : score=$sc status=$st"
}
