# Runs a single Hermes executive board meeting and appends output to a log.
# Intended to be invoked by Windows Task Scheduler (see scripts/install_task.ps1).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Log = Join-Path $Root "data\company\board_meeting_task.log"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content -Path $Log -Value "==== Board meeting run @ $stamp ===="

& $Python -m src.cli company review *>> $Log
Add-Content -Path $Log -Value "==== exit code: $LASTEXITCODE ===="
