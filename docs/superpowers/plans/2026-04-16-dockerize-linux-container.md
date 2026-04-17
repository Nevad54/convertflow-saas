# ConvertFlow Dockerize Linux Container Plan

Last updated: 2026-04-16
Status: In progress
Owner: Codex

## Goal

Package ConvertFlow into a Linux-friendly container image that preserves the current local-first FastAPI app behavior while supporting LibreOffice-based Office-to-PDF conversion and Ollama sidecar integration.

## Scope

This plan covers the initial Phase 2 containerization layer:

- `Dockerfile`
- `.dockerignore`
- integration expectations with `docker-compose.yml`
- validation checklist for Linux-hosted smoke tests

It does not cover deployment platform setup, auth, billing, or broader infra automation.

## Current State

The following are already complete:

- LibreOffice fallback is implemented in `execution/pdf_tools.py`
- `requirements.txt` isolates `pywin32` to Windows only
- initial root-level container files now exist:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
- local non-Docker validation now confirms:
  - `app.py` imports cleanly in the project venv
  - the FastAPI app serves `/` successfully on port `8080`
  - the app exposes `/health` for readiness checks
  - `python test_all_tools.py` passes end-to-end with `77 passed, 0 failed, 0 skipped`
  - `docker-compose.yml` now includes an app healthcheck plus `restart: unless-stopped` for the long-running services
  - `test_all_tools.py` can now wait for the configured Ollama model before enabling Ollama-backed smoke tests via `OLLAMA_WAIT_FOR_MODEL_SECONDS`
  - the app service now waits for `model-puller` to complete successfully before starting, removing the first-boot Ollama/model race from compose startup
  - the Ollama sidecar image is pinned to `ollama/ollama:0.20.7` instead of floating on `latest`
  - the Docker image now installs `fonts-dejavu-core`, `fonts-liberation`, and `fontconfig` to reduce Linux-only document rendering drift

The remaining work is validation and refinement on a machine that has Docker installed.

## File Map

| File | Action | Purpose |
|---|---|---|
| `Dockerfile` | maintain | Linux app image with Python, LibreOffice, and Tesseract |
| `.dockerignore` | maintain | Reduce build context and keep local-only files out of image |
| `docker-compose.yml` | validate alongside Dockerfile | App + Ollama sidecar + model pull bootstrap |

## Dockerfile Requirements

The Docker image should:

- use a slim Python base image
- install `libreoffice` so Office-to-PDF fallback works on Linux
- install `tesseract-ocr` for OCR-backed flows
- install Python dependencies from `requirements.txt`
- copy the app source into `/app`
- create `/app/.tmp/uploads` and `/app/.tmp/outputs`
- expose port `8080`
- start with:

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

## .dockerignore Requirements

The build context should exclude:

- virtual environments
- temp/output folders
- local automation folders
- caches
- screenshots and other bulky local artifacts
- `.env`
- credential files

## Validation Steps

Run these on a machine with Docker available:

1. Parse the compose file:

```bash
docker compose config --quiet
```

2. Build and start services:

```bash
docker compose up --build
```

3. Verify runtime behavior:

- app responds at `http://localhost:8080`
- app readiness responds at `http://localhost:8080/health`
- Ollama healthcheck passes
- `model-puller` completes successfully
- `gemma4:e4b` is available inside the shared Ollama volume
- app starts only after `model-puller` finishes successfully on a first boot

4. Smoke-test Linux conversion flows:

- upload `.docx` and convert to PDF
- upload `.pptx` and convert to PDF
- upload `.xlsx` and convert to PDF

Expected result: all three work through the LibreOffice fallback path without Windows COM.

For containerized smoke runs, set a model wait timeout if the Ollama sidecar may still be pulling on first boot, for example:

```bash
OLLAMA_HOST=http://ollama:11434 OLLAMA_OCR_MODEL=gemma4:e4b OLLAMA_WAIT_FOR_MODEL_SECONDS=180 python test_all_tools.py
```

## Failure Handling

If validation fails:

1. read the exact Docker/build/runtime error
2. fix the container files or related deterministic execution code
3. rerun the failing validation step
4. update this plan and `.tmp/codex_handoff.md` with the learning

If the fix would require paid APIs or external credits, stop and confirm before retrying.

## Exit Criteria

- `docker compose config --quiet` passes
- `docker compose up --build` succeeds
- app starts on Linux container runtime
- LibreOffice-backed Office-to-PDF works in-container
- Ollama sidecar wiring is confirmed functional

## Notes

- This work should be framed as deployment hardening for a local-first workflow, not as proprietary cloning.
- If additional Linux packages are required during validation, add only what is justified by actual runtime errors.
- Docker CLI is still unavailable in the current worker environment, so `docker compose config --quiet` and `docker compose up --build` remain the blocking validation steps.
- Ollama image pin note: the compose file now uses `ollama/ollama:0.20.7` so future validation runs are deterministic across sessions.
- Font note: the image now includes a small font baseline for LibreOffice/PDF fidelity. If the first containerized Office conversions still drift, add only the missing families justified by those outputs.
