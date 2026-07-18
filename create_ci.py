from pathlib import Path

# Create directories
Path(".github/workflows").mkdir(parents=True, exist_ok=True)

# Dockerfile.cpu
dockerfile_cpu = """FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    build-essential \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

EXPOSE 8501
CMD ["uv", "run", "carpet-designer", "serve"]
"""

# Dockerfile.cuda
dockerfile_cuda = """FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \\
    python3.11 \\
    python3-pip \\
    build-essential \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3.11 /usr/bin/python

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

EXPOSE 8501
CMD ["uv", "run", "carpet-designer", "serve"]
"""

# compose.yaml
compose_yaml = """services:
  carpet-designer:
    build:
      context: .
      dockerfile: Dockerfile.cpu
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./artifacts:/app/artifacts
"""

# compose.gpu.yaml
compose_gpu_yaml = """services:
  carpet-designer:
    build:
      context: .
      dockerfile: Dockerfile.cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
"""

# CI Workflows
ci_yaml = """name: CI

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install uv
        uv pip install --system -e ".[dev]"
    - name: Lint
      run: |
        uv run ruff check .
        uv run ruff format --check .
    - name: Test
      run: |
        uv run pytest -q
"""

sec_yaml = """name: Security

on:
  schedule:
    - cron: '0 0 * * 0'
  push:
    branches: [ main ]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Bandit
      run: |
        pip install bandit
        bandit -r src/
"""

Path("Dockerfile.cpu").write_text(dockerfile_cpu, encoding="utf-8")
Path("Dockerfile.cuda").write_text(dockerfile_cuda, encoding="utf-8")
Path("compose.yaml").write_text(compose_yaml, encoding="utf-8")
Path("compose.gpu.yaml").write_text(compose_gpu_yaml, encoding="utf-8")
Path(".github/workflows/ci.yml").write_text(ci_yaml, encoding="utf-8")
Path(".github/workflows/security.yml").write_text(sec_yaml, encoding="utf-8")
