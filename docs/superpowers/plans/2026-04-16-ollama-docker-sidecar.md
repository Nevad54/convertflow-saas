# Ollama Docker Sidecar Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run Ollama as a Docker sidecar container so the app works in Docker on Linux, where `start.bat` (which launches `ollama serve` on the host) is unavailable.

**Audit result (2026-04-16):** `app.py` has **zero** hardcoded Ollama URLs. All runtime Ollama URLs are already env-var driven via `os.environ.get("OLLAMA_HOST", "http://localhost:11434")` in `execution/pdf_tools.py` (line 465) and `execution/converter.py` (lines 378, 384). **Zero app code changes needed.** The only work is creating `docker-compose.yml` and wiring in a model-pull step.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `docker-compose.yml` | Create at project root | App + Ollama services + model-puller init service |

**No other files change.**

---

## Task 1: Create `docker-compose.yml`

**Files:**
- Create: `docker-compose.yml` at project root

- [ ] **Step 1: Verify no `docker-compose.yml` exists yet**

```bash
ls "d:/Web App/Converter/docker-compose.yml" 2>/dev/null && echo "EXISTS" || echo "OK to create"
```

Expected: `OK to create`

- [ ] **Step 2: Create `docker-compose.yml` at project root**

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_OCR_MODEL=gemma4:e4b
    depends_on:
      ollama:
        condition: service_healthy
    volumes:
      - ./.tmp:/app/.tmp

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 15s

  model-puller:
    image: ollama/ollama:latest
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      - OLLAMA_HOST=http://ollama:11434
    entrypoint: ["ollama"]
    command: ["pull", "gemma4:e4b"]
    restart: "no"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

**Notes on design choices:**
- `model-puller` is a one-shot init container using the same `ollama/ollama` image — it runs `ollama pull gemma4:e4b` against the already-running `ollama` service and exits. On subsequent `docker compose up`, the model is already in `ollama_data` volume, so the pull is near-instant.
- `restart: "no"` on `model-puller` ensures it doesn't loop on success.
- `app` uses `depends_on: ollama: condition: service_healthy` — the app won't start until Ollama passes its healthcheck. The model-puller runs in parallel with the app; if the app starts before the model is pulled, the AI engines fall through to the Basic engine (graceful degradation already built in).
- `OLLAMA_OCR_MODEL=gemma4:e4b` is set explicitly so the compose file is self-documenting and the value can be overridden without touching code.
- `./.tmp:/app/.tmp` maps the local temp/output directory so converted files are accessible from the host during development.

- [ ] **Step 3: Validate the compose file parses**

```bash
docker compose -f "d:/Web App/Converter/docker-compose.yml" config --quiet
```

Expected: exit 0, no errors. If Docker is not installed on the dev machine, skip this step and note it.

- [ ] **Step 4: Smoke-test model-puller command exists on the ollama image**

This is a documentation check only — no command to run. Confirm `ollama pull` is a valid subcommand of the `ollama/ollama` image. It is (the image ships the full `ollama` CLI).

---

## Task 2: Update SAAS_PLAN.md

**Files:**
- Modify: `SAAS_PLAN.md`

- [ ] **Step 1: Update Phase 1 Blocker 2 status in SAAS_PLAN.md**

Find:
```
| Phase 1 — Ollama Docker sidecar | _write before starting_ |
```

Replace with:
```
| Phase 1 — Ollama Docker sidecar | `docs/superpowers/plans/2026-04-16-ollama-docker-sidecar.md` |
```

Also find and update the Blocker 2 entry in the "Current Blockers" section:
```
2. Ollama Docker sidecar → need to audit all hardcoded `localhost:11434` URLs first
```

Replace with:
```
2. Ollama Docker sidecar → sub-plan ready, execute Phase 1 Blocker 2
```

- [ ] **Step 2: Verify the edit looks correct**

```bash
grep -n "Ollama Docker sidecar\|localhost:11434" "d:/Web App/Converter/SAAS_PLAN.md"
```

---

## Verification Checklist

After both tasks are done, confirm:

- [ ] `docker-compose.yml` exists at project root
- [ ] `docker compose config --quiet` exits 0 (or Docker not installed — skip)
- [ ] SAAS_PLAN.md Sub-Plans Index shows the plan file path for Ollama Docker sidecar
- [ ] SAAS_PLAN.md Current Blockers entry updated to "sub-plan ready"
- [ ] No app code was modified (all OLLAMA_HOST refs were already env-var-driven)

---

## Notes for Future Sessions

- **App code is already ready.** `app.py` has no hardcoded Ollama host, and `execution/pdf_tools.py:465` plus `execution/converter.py:378,384` all use `os.environ.get("OLLAMA_HOST", "http://localhost:11434")`. When Docker sets `OLLAMA_HOST=http://ollama:11434`, the app picks it up automatically.
- **Model name** is `gemma4:e4b` — set as default in `OLLAMA_OCR_MODEL` env var in both `pdf_tools.py:466` and `converter.py:379`.
- **`start.bat`** is Windows-only and not relevant to Docker. It sets `OLLAMA_HOME`/`OLLAMA_MODELS` to `D:\.ollama` — these are host-side env vars for the Windows Ollama install, not needed in Docker.
- **`test_all_tools.py:363`** has one hardcoded `http://localhost:11434` — this is the test harness checking if Ollama is reachable locally. Acceptable for a test file; no change needed.
- **Minor cleanup opportunity (non-blocking):** `converter.py:384` calls `os.environ.get("OLLAMA_HOST", ...)` a second time inside the same function instead of reusing the `ollama_url` variable captured at line 378. This is harmless but slightly wasteful. Fix in a future cleanup pass, not a Phase 1 blocker.
- After Phase 2 (Dockerfile), the `Dockerfile` must install LibreOffice: `apt-get install -y libreoffice` — this is already in the Phase 2 Dockerfile spec in SAAS_PLAN.md.
