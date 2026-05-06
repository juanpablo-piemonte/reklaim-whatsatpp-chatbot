.PHONY: run stop restart test logs install clean _guard_port

VENV    := .venv
PID_DIR := .pids
LOG_DIR := logs
PORT    := 8000
APP     := app.core.api.main:app

# ── Start ────────────────────────────────────────────────────────────────────

run: _guard_port stop
	@mkdir -p $(PID_DIR) $(LOG_DIR)
	@echo "Starting Uvicorn on :$(PORT)..."
	@$(VENV)/bin/uvicorn $(APP) --reload --port $(PORT) \
		> $(LOG_DIR)/uvicorn.log 2>&1 & \
	UVICORN_PID=$$!; \
	echo $$UVICORN_PID > $(PID_DIR)/uvicorn.pid; \
	echo "  PID $$UVICORN_PID — waiting for :$(PORT)..."; \
	READY=0; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 0.5; \
		if ! kill -0 $$UVICORN_PID 2>/dev/null; then \
			echo ""; \
			echo "Uvicorn exited — $(LOG_DIR)/uvicorn.log:"; \
			echo ""; \
			tail -30 $(LOG_DIR)/uvicorn.log; \
			rm -f $(PID_DIR)/uvicorn.pid; \
			exit 1; \
		fi; \
		if lsof -ti :$(PORT) >/dev/null 2>&1; then \
			READY=1; break; \
		fi; \
	done; \
	if [ "$$READY" -eq 0 ]; then \
		echo ""; \
		echo "Timed out waiting for :$(PORT) after 5s — $(LOG_DIR)/uvicorn.log:"; \
		echo ""; \
		tail -30 $(LOG_DIR)/uvicorn.log; \
		kill $$UVICORN_PID 2>/dev/null || true; \
		rm -f $(PID_DIR)/uvicorn.pid; \
		exit 1; \
	fi; \
	echo ""; \
	echo "  API  → http://localhost:$(PORT)"; \
	echo "  Docs → http://localhost:$(PORT)/docs"; \
	echo ""; \
	echo "  make logs   tail live output"; \
	echo "  make stop   stop the service"

# ── Guard: fail loudly if a non-uvicorn process owns PORT ───────────────────

_guard_port:
	@PIDS=$$(lsof -ti :$(PORT) 2>/dev/null) || true; \
	if [ -z "$$PIDS" ]; then exit 0; fi; \
	for PID in $$PIDS; do \
		CMD=$$(ps -p $$PID -o command= 2>/dev/null || echo "unknown"); \
		if ! echo "$$CMD" | grep -q "uvicorn"; then \
			echo "ERROR: port $(PORT) is in use by a non-uvicorn process:"; \
			echo "  PID $$PID: $$CMD"; \
			echo "Stop that process manually or run with a different PORT."; \
			exit 1; \
		fi; \
	done; \
	echo "  Port $(PORT) held by uvicorn — restarting."

# ── Stop ─────────────────────────────────────────────────────────────────────

stop:
	@FOUND=0; \
	if [ -f $(PID_DIR)/uvicorn.pid ]; then \
		PID=$$(cat $(PID_DIR)/uvicorn.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			echo "  SIGTERM → PID $$PID"; \
			kill $$PID 2>/dev/null || true; \
			FOUND=1; \
		fi; \
		rm -f $(PID_DIR)/uvicorn.pid; \
	fi; \
	sleep 0.5; \
	for PID in $$(lsof -ti :$(PORT) 2>/dev/null); do \
		CMD=$$(ps -p $$PID -o command= 2>/dev/null | cut -c1-80 || echo "unknown"); \
		echo "  SIGKILL → PID $$PID ($$CMD)"; \
		kill -9 $$PID 2>/dev/null || true; \
		FOUND=1; \
	done; \
	if [ "$$FOUND" -eq 0 ]; then \
		echo "  Nothing was running."; \
	else \
		echo "  Stopped."; \
	fi

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
