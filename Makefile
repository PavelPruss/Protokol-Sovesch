SHELL := cmd

UV ?= uv
APP ?= web_app.py
DOCKER_COMPOSE ?= docker compose
RUN_DIR := .run
PID_FILE := $(RUN_DIR)\web_app.pid
LOG_FILE := $(RUN_DIR)\web_app.log
ERR_LOG_FILE := $(RUN_DIR)\web_app.err.log
PS := powershell -NoProfile -ExecutionPolicy Bypass -Command

.PHONY: help sync start stop status restart run logs clean dc-up dc-down dc-restart dc-logs dc-ps status-all

help:
	@echo Commands:
	@echo   make sync       - install dependencies with uv
	@echo   make start      - start app in background (single instance)
	@echo   make stop       - stop app
	@echo   make status     - show app status
	@echo   make restart    - restart app
	@echo   make run        - run app in foreground
	@echo   make logs       - show log file path
	@echo   make clean      - remove state files
	@echo   make dc-up      - start docker compose in background
	@echo   make dc-down    - stop docker compose
	@echo   make dc-restart - restart docker compose
	@echo   make dc-logs    - tail docker compose logs
	@echo   make dc-ps      - show docker compose status
	@echo   make status-all - show local and docker status

sync:
	@$(UV) sync

start: sync
	@$(PS) "if (-not (Test-Path '$(RUN_DIR)')) { New-Item -ItemType Directory -Path '$(RUN_DIR)' | Out-Null }; if (Test-Path '$(PID_FILE)') { $$procId = Get-Content '$(PID_FILE)' -ErrorAction SilentlyContinue; if ($$procId -and (Get-Process -Id $$procId -ErrorAction SilentlyContinue)) { throw 'Already running. Use make stop first.' } else { Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue } }; $$proc = Start-Process -FilePath '$(UV)' -ArgumentList 'run','python','$(APP)' -RedirectStandardOutput '$(LOG_FILE)' -RedirectStandardError '$(ERR_LOG_FILE)' -WindowStyle Hidden -PassThru; $$proc.Id | Set-Content '$(PID_FILE)'; Start-Sleep -Seconds 1; if (Get-Process -Id $$proc.Id -ErrorAction SilentlyContinue) { Write-Host ('Started PID=' + $$proc.Id + '. Logs: $(LOG_FILE), $(ERR_LOG_FILE)') } else { Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue; throw 'Failed to start app. Check logs.' }"

stop:
	@$(PS) "if (-not (Test-Path '$(PID_FILE)')) { Write-Host 'Not running (no PID file).'; exit 0 }; $$procId = Get-Content '$(PID_FILE)' -ErrorAction SilentlyContinue; if ($$procId -and (Get-Process -Id $$procId -ErrorAction SilentlyContinue)) { Stop-Process -Id $$procId -Force; Write-Host ('Stopping PID=' + $$procId + '...') } else { Write-Host ('Process not active (PID=' + $$procId + ').') }; Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue; Write-Host 'Stopped.'"

status:
	@$(PS) "if (-not (Test-Path '$(PID_FILE)')) { Write-Host 'Status: stopped'; exit 0 }; $$procId = Get-Content '$(PID_FILE)' -ErrorAction SilentlyContinue; if ($$procId -and (Get-Process -Id $$procId -ErrorAction SilentlyContinue)) { Write-Host ('Status: running (PID=' + $$procId + ')') } else { Write-Host 'Status: stopped (stale PID file)' }"

restart: stop start

run: sync
	@$(PS) "if (-not (Test-Path '$(RUN_DIR)')) { New-Item -ItemType Directory -Path '$(RUN_DIR)' | Out-Null }; if (Test-Path '$(PID_FILE)') { $$procId = Get-Content '$(PID_FILE)' -ErrorAction SilentlyContinue; if ($$procId -and (Get-Process -Id $$procId -ErrorAction SilentlyContinue)) { throw 'Already running. Use make stop first.' } else { Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue } }; $$global:PID | Set-Content '$(PID_FILE)'; try { Write-Host 'Running in current window. Press Ctrl+C to stop.'; & '$(UV)' run python '$(APP)' } finally { Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue }"

logs:
	@echo Stdout log: $(LOG_FILE)
	@echo Stderr log: $(ERR_LOG_FILE)

clean:
	@$(PS) "Remove-Item '$(PID_FILE)' -Force -ErrorAction SilentlyContinue; Write-Host 'State files cleaned.'"

dc-up:
	@$(DOCKER_COMPOSE) up --build -d

dc-down:
	@$(DOCKER_COMPOSE) down

dc-restart: dc-down dc-up

dc-logs:
	@$(DOCKER_COMPOSE) logs -f --tail=150

dc-ps:
	@$(DOCKER_COMPOSE) ps

status-all:
	@echo Local:
	@$(MAKE) status
	@echo Docker:
	@$(DOCKER_COMPOSE) ps
