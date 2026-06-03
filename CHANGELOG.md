# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.4] - 2026-06-03

### Added

- `LICENSE` — MIT License (Copyright (c) 2025 sumipan)
- `README.md` — project overview, installation, quick start, development setup, license
- `.github/workflows/test.yml` — CI workflow (ruff → mypy → pytest) on push/PR to main
- `.gitignore` — Python standard ignore patterns
- `CHANGELOG.md` — this file
- `pyproject.toml` — added `description`, `authors`, `license` fields; extended `dev` extras with ruff, mypy, pytest-cov; added `[tool.ruff]` and `[tool.mypy]` sections
