# set_copilot_env.ps1
# Sæt miljøvariabler til GitHub Copilot AI-provider for enrichment scripts
# Kør denne i PowerShell før du starter Python-scriptet

# Sæt dit Copilot-token her (indsæt manuelt eller hent fra VS Code hvis muligt)
$env:GITHUB_TOKEN = "GITHUB_PAT_REDACTED"
$env:DOMAIN_ENGINE_AI_PROVIDER = "copilot"
Write-Host "Miljøvariabler sat. Klar til enrichment med Copilot (GPT-4.1)."
Write-Host "Kør nu: python run_ai_enrichment.py --domain identity_access"
