# -------- Settings --------
SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip

# Default target
.DEFAULT_GOAL := help

# -------- Targets --------

.PHONY: help
help:
	@echo ""
	@echo "Usage:"
	@echo "  make venv        Create & upgrade the local Python virtual environment"
	@echo "  make install     Install Python dependencies from requirements.txt"
	@echo "  make data        Fetch prices & generate sample events (Day 1)"
	@echo "  make train       Train models and save artifacts (Day 4)"
	@echo "  make backtest    Run backtests and export plots (Day 5)"
	@echo "  make serve       Start the API or demo service (Day 6)"
	@echo "  make clean       Remove generated artifacts and processed data"
	@echo ""

.PHONY: venv
venv:
	@echo "[venv] Creating virtual environment at .venv ..."
	@python3 -m venv .venv
	@echo "[venv] Upgrading pip/setuptools/wheel ..."
	@$(PIP) install --upgrade pip setuptools wheel

.PHONY: install
install:
	@test -d .venv || (echo "[install] .venv not found. Run 'make venv' first." && false)
	@echo "[install] Installing dependencies from requirements.txt ..."
	@$(PIP) install -r requirements.txt
	@echo "[install] Done."

.PHONY: data
data:
	@test -d .venv || (echo "[data] .venv not found. Run 'make venv' and 'make install' first." && false)
	@mkdir -p data/raw data/processed
	@if [ -f model/scripts/fetch_data.py ]; then \
		echo "[data] Running fetch_data.py ..."; \
		$(PY) model/scripts/fetch_data.py; \
	else \
		echo "[data] Placeholder: create 'model/scripts/fetch_data.py' to download prices and write:"; \
		echo "        - data/processed/prices.parquet"; \
		echo "        - data/processed/events.csv"; \
	fi

.PHONY: train
train:
	@test -d .venv || (echo "[train] .venv not found. Run 'make venv' and 'make install' first." && false)
	@mkdir -p model/artifacts
	@if [ -f model/train.py ]; then \
		echo "[train] Training model ..."; \
		$(PY) model/train.py; \
	else \
		echo "[train] Placeholder: add 'model/train.py' to train and save artifacts into model/artifacts/"; \
	fi

.PHONY: backtest
backtest:
	@test -d .venv || (echo "[backtest] .venv not found. Run 'make venv' and 'make install' first." && false)
	@mkdir -p docs
	@if [ -f research/backtest.py ]; then \
		echo "[backtest] Running backtest ..."; \
		$(PY) research/backtest.py; \
	else \
		echo "[backtest] Placeholder: add 'research/backtest.py' to compute metrics and export plots into docs/"; \
	fi

.PHONY: serve
serve:
	@if [ -f service/target/*.jar ]; then \
		echo "[serve] Running Spring Boot JAR ..."; \
		java -jar service/target/*.jar; \
	elif [ -f service/run.sh ]; then \
		echo "[serve] Running service/run.sh ..."; \
		bash service/run.sh; \
	else \
		echo "[serve] Placeholder: build your Spring Boot app (mvn package) or add service/run.sh"; \
	fi

.PHONY: clean
clean:
	@echo "[clean] Removing generated files ..."
	@rm -rf data/processed/* || true
	@rm -rf model/artifacts/* || true
	@rm -rf docs/*.png docs/*.pdf || true
	@echo "[clean] Done."
