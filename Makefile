.PHONY: help install dev run test test-cov lint format docker docker-run clean

PYTHON ?= python
VENV ?= venv
ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
else
	BIN := $(VENV)/bin
endif

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:             ## Create venv and install runtime deps
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -r requirements.txt

dev:                 ## Install dev deps and pre-commit hooks
	$(BIN)/pip install -r requirements-dev.txt
	$(BIN)/pre-commit install

run:                 ## Run the dev server with hot reload
	$(BIN)/uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:                ## Run the test suite
	$(BIN)/pytest

test-cov:            ## Run tests with coverage report
	$(BIN)/pytest --cov=app --cov-report=term --cov-report=html

lint:                ## Run linters
	$(BIN)/ruff check app tests
	$(BIN)/ruff format --check app tests

format:              ## Auto-format the codebase
	$(BIN)/ruff check --fix app tests
	$(BIN)/ruff format app tests

docker:              ## Build the production Docker image
	docker build -t smart-invoice-generator:latest .

docker-run:          ## Run the Docker image locally on :8000
	docker compose up --build

clean:               ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov coverage.xml dist build
