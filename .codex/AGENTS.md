# Repository Guidelines

## Project Structure & Module Organization

This is an early Python project for Fitfolio, an AI-assisted resume and job posting analysis tool. Current files are minimal:

- `main.py`: placeholder Python entry point.
- `pyproject.toml`: project metadata and runtime dependencies.
- `uv.lock`: locked dependency graph; keep it committed when dependencies change.
- `docs/architecture.html`: detailed Korean architecture document for the planned FastAPI, LangGraph, OCR, and analysis pipeline.

The architecture document proposes future packages such as `api/`, `core/`, `app/`, and `tests/`. Follow that structure when adding implementation code: API routes in `api/`, orchestration and domain logic in `core/`, UI code in `app/`, and automated tests in `tests/`.

## Build, Test, and Development Commands

Use `uv` for dependency management because this repository includes `uv.lock`.

- `uv sync`: create/update the virtual environment from `pyproject.toml` and `uv.lock`.
- `uv run python main.py`: run the current entry point.
- `uv add <package>`: add a dependency and update the lockfile.
- `uv run pytest`: run tests once a `tests/` suite exists.

If FastAPI code is added under `api/main.py`, prefer `uv run fastapi dev api/main.py` for local development.

## Coding Style & Naming Conventions

Target Python `>=3.13`. Use 4-space indentation, type hints for public functions, and Pydantic models for request, response, and pipeline data contracts. Prefer descriptive snake_case names for modules, functions, and variables; use PascalCase for classes and Pydantic models.

Keep orchestration code separate from provider integrations: LangGraph flow belongs in `core/graph/`, while LLM and OCR provider wrappers should live under dedicated provider modules.

## Testing Guidelines

No tests exist yet. Add `pytest` tests under `tests/` as implementation appears. Name files `test_<feature>.py` and test functions `test_<behavior>()`. Use mock LLM/OCR providers for deterministic tests, especially around structured output validation, score ranges, and security guards.

## Commit & Pull Request Guidelines

This directory currently has no `.git` history available, so no existing commit convention can be inferred. Use concise imperative commits such as `Add URL guard validation` or `Implement resume parser schema`.

Pull requests should include a short summary, test results, linked issue or task context, and screenshots only for UI changes. Note any security or privacy impact when changing document ingestion, logging, LLM prompts, or external provider calls.

## Security & Configuration Tips

Never commit API keys, resumes, cover letters, or real personal data. Keep secrets in environment variables or local secret stores. Avoid logging raw uploaded documents, OCR output, prompts, or LLM responses unless they are synthetic and clearly marked as test fixtures.
