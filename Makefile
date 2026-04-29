.PHONY: run stop restart test logs install clean

VENV    := .venv
PID_DIR := .pids
LOG_DIR := logs

# ── Start everything ────────────────────────────────────────────────────────

run: stop
	@mkdir -p $(PID_DIR) $(LOG_DIR)
	@echo "Starting Uvicorn..."
	$(VENV)/bin/uvicorn app.api.main:app --reload --port 8000 \
		> $(LOG_DIR)/uvicorn.log 2>&1 & echo $$! > $(PID_DIR)/uvicorn.pid
	@echo ""
	@echo "Service running:"
	@echo "  API  → http://localhost:8000"
	@echo "  Docs → http://localhost:8000/docs"
	@echo ""
	@echo "  make logs    tail live output"
	@echo "  make stop    stop the service"

# ── Stop everything ──────────────────────────────────────────────────────────

stop:
	@echo "Stopping services..."
	@-[ -f $(PID_DIR)/uvicorn.pid ] && kill $$(cat $(PID_DIR)/uvicorn.pid) 2>/dev/null; rm -f $(PID_DIR)/uvicorn.pid
	@-pkill -f "uvicorn app.api.main:app" 2>/dev/null; true
	@echo "Done."

restart: run

# ── Dev helpers ──────────────────────────────────────────────────────────────

logs:
	@tail -f $(LOG_DIR)/uvicorn.log

test:
	$(VENV)/bin/pytest -v

# ── First-time setup ─────────────────────────────────────────────────────────

install:
	python3.12 -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[dev]"
	@cp -n .env.example .env 2>/dev/null \
		&& echo ".env created — fill in your credentials before running 'make run'." \
		|| echo ".env already exists."

# ── Teardown ─────────────────────────────────────────────────────────────────

clean: stop
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf $(PID_DIR) $(LOG_DIR)
