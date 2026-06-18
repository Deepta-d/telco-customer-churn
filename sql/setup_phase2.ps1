# Phase 2 setup — run from project root
#
# If you get "cannot be loaded because running scripts is disabled", use ONE of:
#   python sql/setup_phase2.py
#   sql\setup_phase2.bat
#   powershell -ExecutionPolicy Bypass -File .\sql\setup_phase2.ps1 -Password "your_password"
#
# Do NOT use the literal text YOUR_MYSQL_PASSWORD — replace with your real MySQL password.
# Or create sql/.env with MYSQL_PASSWORD=your_password and run: python sql/setup_phase2.py

param(
    [Parameter(Mandatory = $true)]
    [string]$Password
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if ($Password -eq "YOUR_MYSQL_PASSWORD" -or $Password -eq "your_password_here") {
    Write-Host "Error: Replace YOUR_MYSQL_PASSWORD with your actual MySQL root password." -ForegroundColor Red
    Write-Host "Or run: python sql/setup_phase2.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "Step 1: Prepare SQL-ready dataset..." -ForegroundColor Cyan
python "$Root\sql\prepare_sql_dataset.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Step 2: Load into MySQL..." -ForegroundColor Cyan
python "$Root\sql\load_to_mysql.py" -p $Password
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nMySQL load failed. Common fixes:" -ForegroundColor Red
    Write-Host "  1. Verify password works in MySQL Workbench" -ForegroundColor Yellow
    Write-Host "  2. Ensure MySQL80 service is running" -ForegroundColor Yellow
    Write-Host "  3. Try: python sql/setup_phase2.py" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Step 3: Run analysis queries..." -ForegroundColor Cyan
$env:MYSQL_PASSWORD = $Password
python "$Root\sql\run_queries.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nPhase 2 complete." -ForegroundColor Green
