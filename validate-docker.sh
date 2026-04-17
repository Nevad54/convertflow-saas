#!/usr/bin/env bash
# validate-docker.sh — ConvertFlow Docker validation script
# Run this on any machine with Docker + Docker Compose installed.
#
# Usage:
#   bash validate-docker.sh              # full validation
#   bash validate-docker.sh --no-smoke   # skip smoke tests (fast sanity check)
#
# What it does:
#   1. Validates the compose file
#   2. Builds images and starts containers
#   3. Waits for app + Ollama to become healthy
#   4. Checks /health endpoint
#   5. Runs the smoke test suite against the running container
#   6. Tears down containers (volumes preserved for model cache)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

SKIP_SMOKE=false
if [[ "${1:-}" == "--no-smoke" ]]; then
  SKIP_SMOKE=true
fi

info()    { echo -e "${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[PASS]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
fail()    { echo -e "${RED}[FAIL]${RESET}  $*"; exit 1; }

COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"
APP_URL="http://localhost:8080"
HEALTH_URL="${APP_URL}/health"

# ── Step 1: Validate compose config ──────────────────────────────────────────
info "Validating docker-compose.yml…"
docker compose -f "$COMPOSE_FILE" config --quiet \
  && success "docker-compose.yml is valid" \
  || fail "docker-compose.yml has errors"

# ── Step 2: Build and start ───────────────────────────────────────────────────
info "Building and starting containers (this may take several minutes on first run)…"
docker compose -f "$COMPOSE_FILE" up --build --detach

# ── Step 3: Wait for app health ───────────────────────────────────────────────
info "Waiting for app container to become healthy (up to 3 minutes)…"
DEADLINE=$(( $(date +%s) + 180 ))
until curl -sf "${HEALTH_URL}" > /dev/null 2>&1; do
  if [[ $(date +%s) -gt $DEADLINE ]]; then
    docker compose -f "$COMPOSE_FILE" logs app
    fail "App did not become healthy within 3 minutes"
  fi
  sleep 3
done
success "App is healthy"

# ── Step 4: Check /health response ───────────────────────────────────────────
info "Checking /health endpoint…"
HEALTH_BODY=$(curl -sf "${HEALTH_URL}")
if echo "$HEALTH_BODY" | grep -q '"status":"ok"'; then
  success "/health → ${HEALTH_BODY}"
else
  fail "/health returned unexpected body: ${HEALTH_BODY}"
fi

# ── Step 5: Check Ollama sidecar ─────────────────────────────────────────────
info "Checking Ollama sidecar…"
OLLAMA_URL="http://localhost:11434/api/tags"
OLLAMA_BODY=$(curl -sf "${OLLAMA_URL}" || echo "")
if [[ -z "$OLLAMA_BODY" ]]; then
  warn "Ollama is not reachable on host port 11434 — this is OK if port is not exposed"
else
  if echo "$OLLAMA_BODY" | grep -q "gemma4"; then
    success "Ollama healthy and gemma4 model present"
  else
    warn "Ollama reachable but gemma4 model not yet listed — model-puller may still be running"
  fi
fi

# ── Step 6: Smoke tests ───────────────────────────────────────────────────────
if [[ "$SKIP_SMOKE" == "true" ]]; then
  warn "Skipping smoke tests (--no-smoke flag)"
else
  info "Running smoke test suite against the running container…"
  info "  OLLAMA_HOST=http://localhost:11434  (using host-mapped port)"
  info "  OLLAMA_WAIT_FOR_MODEL_SECONDS=180"

  # Run tests from the host using the host-mapped port
  OLLAMA_HOST=http://localhost:11434 \
  OLLAMA_OCR_MODEL=gemma4:e4b \
  OLLAMA_WAIT_FOR_MODEL_SECONDS=180 \
    python test_all_tools.py \
    && success "Smoke tests passed" \
    || fail "Smoke tests failed — check output above"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}Docker validation complete.${RESET}"
echo ""
echo "Containers are still running. To stop:"
echo "  docker compose down"
echo "To stop and wipe volumes (removes pulled Ollama model):"
echo "  docker compose down -v"
