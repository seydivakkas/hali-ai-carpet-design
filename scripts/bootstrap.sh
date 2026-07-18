#!/usr/bin/env bash
# Halı AI Carpet Design — Bootstrap Script (Linux/macOS)
# Usage: bash scripts/bootstrap.sh

set -euo pipefail

echo "=== Halı AI Carpet Design Bootstrap ==="

# Check uv
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/"
    exit 1
fi

# Create venv
echo "Creating Python 3.11 virtual environment..."
uv venv --python 3.11

# Install all dependencies
echo "Installing dependencies..."
uv sync --all-extras

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
uv run pre-commit install

# Run doctor
echo "Running system doctor..."
uv run carpet-designer doctor

echo "=== Bootstrap complete ==="
