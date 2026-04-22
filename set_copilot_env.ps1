# set_copilot_env.ps1
# Sæt miljøvariabler til GitHub Copilot AI-provider for enrichment scripts
# Kør denne i PowerShell før du starter Python-scriptet

# Aktiver venv og sæt python-alias så 'python' virker i alle PS-sessioner
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    Set-Alias -Name python -Value $venvPython -Scope Global -Force
    $env:PYTHONIOENCODING = 'utf-8'
    Write-Host "python alias sat til: $venvPython"
} else {
    Write-Warning "venv ikke fundet: $venvPython"
}

# Hent token fra shell-miljø — sæt GITHUB_TOKEN i din PowerShell-profil eller system-miljø.
# Aldrig hardkod tokens her — filen kan ende i git history.
if (-not $env:GITHUB_TOKEN) {
    Write-Error "GITHUB_TOKEN er ikke sat. Sæt den i din PowerShell-profil: `$env:GITHUB_TOKEN = 'dit-token'"
    exit 1
}
$env:DOMAIN_ENGINE_AI_PROVIDER = "copilot"
Write-Host "Miljøvariabler sat. Klar til enrichment med Copilot (GPT-4.1)."
Write-Host "Kør nu: python run_ai_enrichment.py --domain identity_access"
