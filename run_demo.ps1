param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$labPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $labPython)) {
    Write-Host 'Run python -m venv .venv, then .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
Write-Host "PeopleOps demo: http://127.0.0.1:$Port"
& $labPython (Join-Path $PSScriptRoot 'src/web.py') --port $Port
exit $LASTEXITCODE
