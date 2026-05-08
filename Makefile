SHELL := /bin/sh

UV ?= uv
APP ?= web_app.py
RUN_DIR := .run
PID_FILE := $(RUN_DIR)/web_app.pid
LOG_FILE := $(RUN_DIR)/web_app.log

.PHONY: help sync start stop status restart run logs clean

help:
	@echo "Команды:"
	@echo "  make sync    - установить зависимости через uv"
	@echo "  make start   - запустить приложение в фоне (один экземпляр)"
	@echo "  make stop    - остановить приложение"
	@echo "  make status  - показать состояние"
	@echo "  make restart - перезапустить приложение"
	@echo "  make run     - запустить в текущем окне (с блокировкой)"
	@echo "  make logs    - показать путь к логам"
	@echo "  make clean   - удалить временные файлы состояния"

sync:
	@"$(UV)" sync

start: sync
	@mkdir -p "$(RUN_DIR)"
	@if [ -f "$(PID_FILE)" ]; then \
		pid=$$(cat "$(PID_FILE)"); \
		if "$(UV)" run python -c "import os,sys; pid=int(sys.argv[1]); \
try: os.kill(pid,0); print('running'); sys.exit(0) \
except Exception: sys.exit(1)" "$$pid" >/dev/null 2>&1; then \
			echo "Уже запущено (PID=$$pid). Сначала сделайте: make stop"; \
			exit 1; \
		else \
			echo "Найден старый PID-файл, удаляю..."; \
			rm -f "$(PID_FILE)"; \
		fi; \
	fi
	@nohup "$(UV)" run python "$(APP)" >> "$(LOG_FILE)" 2>&1 & echo $$! > "$(PID_FILE)"
	@sleep 1
	@pid=$$(cat "$(PID_FILE)"); \
	if "$(UV)" run python -c "import os,sys; pid=int(sys.argv[1]); \
try: os.kill(pid,0); sys.exit(0) \
except Exception: sys.exit(1)" "$$pid" >/dev/null 2>&1; then \
		echo "Запущено (PID=$$pid). Лог: $(LOG_FILE)"; \
	else \
		echo "Не удалось запустить приложение. Проверьте лог: $(LOG_FILE)"; \
		rm -f "$(PID_FILE)"; \
		exit 1; \
	fi

stop:
	@if [ ! -f "$(PID_FILE)" ]; then \
		echo "Не запущено (PID-файл не найден)."; \
		exit 0; \
	fi
	@pid=$$(cat "$(PID_FILE)"); \
	if "$(UV)" run python -c "import os,sys; pid=int(sys.argv[1]); \
try: os.kill(pid,0); sys.exit(0) \
except Exception: sys.exit(1)" "$$pid" >/dev/null 2>&1; then \
		"$(UV)" run python -c "import os,sys; os.kill(int(sys.argv[1]), 15)" "$$pid" >/dev/null 2>&1 || true; \
		echo "Останавливаю PID=$$pid..."; \
	else \
		echo "Процесс уже не активен (PID=$$pid)."; \
	fi
	@rm -f "$(PID_FILE)"
	@echo "Остановлено."

status:
	@if [ ! -f "$(PID_FILE)" ]; then \
		echo "Статус: остановлено"; \
		exit 0; \
	fi
	@pid=$$(cat "$(PID_FILE)"); \
	if "$(UV)" run python -c "import os,sys; pid=int(sys.argv[1]); \
try: os.kill(pid,0); sys.exit(0) \
except Exception: sys.exit(1)" "$$pid" >/dev/null 2>&1; then \
		echo "Статус: запущено (PID=$$pid)"; \
	else \
		echo "Статус: остановлено (найден старый PID-файл)"; \
	fi

restart: stop start

run: sync
	@mkdir -p "$(RUN_DIR)"
	@if [ -f "$(PID_FILE)" ]; then \
		pid=$$(cat "$(PID_FILE)"); \
		if "$(UV)" run python -c "import os,sys; pid=int(sys.argv[1]); \
try: os.kill(pid,0); sys.exit(0) \
except Exception: sys.exit(1)" "$$pid" >/dev/null 2>&1; then \
			echo "Уже запущено (PID=$$pid). Остановите через: make stop"; \
			exit 1; \
		else \
			echo "Найден старый PID-файл, удаляю..."; \
			rm -f "$(PID_FILE)"; \
		fi; \
	fi
	@echo $$ > "$(PID_FILE)"
	@trap 'rm -f "$(PID_FILE)"' EXIT INT TERM; \
	echo "Запуск в текущем окне. Для остановки: Ctrl+C"; \
	"$(UV)" run python "$(APP)"

logs:
	@echo "Лог файла: $(LOG_FILE)"

clean:
	@rm -f "$(PID_FILE)"
	@echo "Файлы состояния очищены."
