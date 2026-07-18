# Halı AI Carpet Design — Bootstrap Script (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

Write-Host "=== Halı AI Carpet Design Bootstrap ===" -ForegroundColor Cyan

# Check uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: uv not found. Install from https://docs.astral.sh/uv/" -ForegroundColor Red
    exit 1
}

# Create venv
Write-Host "Creating Python 3.11 virtual environment..." -ForegroundColor Yellow
uv venv --python 3.11

# Install all dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
uv sync --all-extras

# Install pre-commit hooks
Write-Host "Installing pre-commit hooks..." -ForegroundColor Yellow
uv run pre-commit install

# Run doctor
Write-Host "Running system doctor..." -ForegroundColor Yellow
uv run carpet-designer doctor

Write-Host "=== Bootstrap complete ===" -ForegroundColor Green
