SHELL := /bin/bash

DEV_COMPOSE := docker compose -f docker-compose.dev.yml
PROD_COMPOSE := docker compose -f docker-compose.prod.yml
BACKUP_DIR ?= /srv/fundamentracker/backups
HEALTH_URL ?= http://127.0.0.1:8000/health/ready
LOG_SERVICES ?=

.PHONY: dev-up dev-down prod-up prod-down logs test frontend-build health backup-db install-systemd

dev-up:
	$(DEV_COMPOSE) up -d --build api frontend

dev-down:
	$(DEV_COMPOSE) down

prod-up:
	$(PROD_COMPOSE) up -d --build

prod-down:
	$(PROD_COMPOSE) down

logs:
	$(PROD_COMPOSE) logs -f --tail=100 $(LOG_SERVICES)

test:
	pytest

frontend-build:
	cd frontend && npm run build

health:
	curl -fsS "$(HEALTH_URL)"

backup-db:
	BACKUP_DIR="$(BACKUP_DIR)" ./scripts/backup-db.sh

install-systemd:
	sudo ./scripts/install-systemd.sh
