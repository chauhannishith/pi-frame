# pi-frame server — Docker shortcuts
# Run from pi-server/: make up, make logs, etc.

COMPOSE  := docker compose
HOST     ?= localhost
PORT     ?= 5001
SERVICE  := pi-frame

.PHONY: help up down stop restart logs logs-f build rebuild ps status shell fetch-frame test

help:
	@echo "pi-frame Docker targets (run from pi-server/)"
	@echo ""
	@echo "  make up          Start container in background"
	@echo "  make up-build    Rebuild image and start"
	@echo "  make build       Build image only"
	@echo "  make down        Stop and remove container"
	@echo "  make stop        Stop container (keeps container)"
	@echo "  make restart     Restart container (pick up app.py changes)"
	@echo "  make rebuild     down + up-build"
	@echo "  make logs        Show recent logs"
	@echo "  make logs-f      Follow logs"
	@echo "  make ps          Show container status"
	@echo "  make status      Same as ps"
	@echo "  make shell       Open bash shell in running container"
	@echo "  make fetch-frame Download latest_frame.bin (HOST=$(HOST) PORT=$(PORT))"
	@echo "  make test        Run pytest on host (PYTHONPATH=app)"
	@echo ""
	@echo "Examples:"
	@echo "  make fetch-frame HOST=192.168.1.42 PORT=5000"

up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up --build -d

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

stop:
	$(COMPOSE) stop

restart:
	$(COMPOSE) restart

rebuild: down up-build

logs:
	$(COMPOSE) logs --tail=100 $(SERVICE)

logs-f:
	$(COMPOSE) logs -f $(SERVICE)

ps status:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec $(SERVICE) bash

fetch-frame:
	curl -f -o latest_frame.bin "http://$(HOST):$(PORT)/get_latest_frame.bin"
	@echo "Saved to latest_frame.bin ($$(wc -c < latest_frame.bin) bytes)"

test:
	PYTHONPATH=app python3 -m pytest tests/ -q
