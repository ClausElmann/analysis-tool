param([string[]]$Domains = @("delivery","web_messages","standard_receivers","sms_group"), [int]$MaxCycles = 5)

$path = "c:\Udvikling\analysis-tool\domains\domain_state.json"
Set-Location c:\Udvikling\analysis-tool

foreach ($domain in $Domains) {
    Write-Host "`n========== $domain ==========" -ForegroundColor Cyan
    $j = Get-Content $path -Raw | ConvertFrom-Json
    Write-Host "PRE: score=$($j.$domain.completeness_score) status=$($j.$domain.status)"

    for ($i = 1; $i -le $MaxCycles; $i++) {
        $j = Get-Content $path -Raw | ConvertFrom-Json
        $j.$domain.status = "in_progress"
        $j._global.active_domain = $domain
        $j | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8

        Write-Host "--- Cycle $i ---"
        & ".venv\Scripts\python.exe" run_domain_engine.py --seeds $domain --once

        $j2 = Get-Content $path -Raw | ConvertFrom-Json
        $st = $j2.$domain.status
        $sc = $j2.$domain.completeness_score
        Write-Host "POST cycle ${i}: score=${sc} status=${st}"

        if ($st -eq "complete") {
            Write-Host "DONE: $domain reached complete" -ForegroundColor Green
            break
        }
    }
}

Write-Host "`n=== FINAL STATE ===" -ForegroundColor Yellow
$j = Get-Content $path -Raw | ConvertFrom-Json
foreach ($d in @("delivery","web_messages","standard_receivers","sms_group")) {
    Write-Host "$d : score=$($j.$d.completeness_score) status=$($j.$d.status)"
}
