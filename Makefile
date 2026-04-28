.PHONY: run stop restart test logs install clean redis-stop

VENV    := .venv
PID_DIR := .pids
LOG_DIR := logs

# ── Start everything ────────────────────────────────────────────────────────

run: stop
	@mkdir -p $(PID_DIR) $(LOG_DIR)
	@echo "Starting Redis..."
	docker-compose up -d
	@echo "Starting Uvicorn..."
	$(VENV)/bin/uvicorn app.api.main:app --reload --port 8000 \
		> $(LOG_DIR)/uvicorn.log 2>&1 & echo $$! > $(PID_DIR)/uvicorn.pid
	@echo "Starting Celery worker..."
	$(VENV)/bin/celery -A app.worker.celery_app worker --loglevel=info \
		> $(LOG_DIR)/celery.log 2>&1 & echo $$! > $(PID_DIR)/celery.pid
	@echo ""
	@echo "All services running:"
	@echo "  API  → http://localhost:8000"
	@echo "  Docs → http://localhost:8000/docs"
	@echo ""
	@echo "  make logs    tail live output from both services"
	@echo "  make stop    stop all services"

# ── Stop everything ──────────────────────────────────────────────────────────

stop:
	@echo "Stopping services..."
	@-[ -f $(PID_DIR)/uvicorn.pid ] && kill $$(cat $(PID_DIR)/uvicorn.pid) 2>/dev/null; rm -f $(PID_DIR)/uvicorn.pid
	@-[ -f $(PID_DIR)/celery.pid  ] && kill $$(cat $(PID_DIR)/celery.pid)  2>/dev/null; rm -f $(PID_DIR)/celery.pid
	@-pkill -f "uvicorn app.api.main:app" 2>/dev/null; true
	@-pkill -f "celery.*reklaim"          2>/dev/null; true
	@echo "Done."

restart: run

# ── Dev helpers ──────────────────────────────────────────────────────────────

logs:
	@tail -f $(LOG_DIR)/uvicorn.log $(LOG_DIR)/celery.log

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
	docker-compose down
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf $(PID_DIR) $(LOG_DIR)

redis-stop:
	docker-compose stop
