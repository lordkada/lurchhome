.PHONY: setup build up down restart logs logs-ha status clean backup restore install install-dev shell test lint format run

# Colori per output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

setup:
	@echo "$(YELLOW)Setup del progetto...$(NC)"
	@mkdir -p docker/data/homeassistant/config
	@if [ ! -f .env ]; then cp .env.example .env; echo "$(GREEN)File .env built from template$(NC)"; fi
	@echo "$(GREEN)Setup completed!$(NC)"

build-docker:
	@echo "$(YELLOW)Building services...$(NC)"
	docker-compose build

up-docker:
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d

down-docker:
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down

restart-docker:
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose restart

logs-docker:
	docker-compose logs -f

logs-docker-ha:
	docker-compose logs -f homeassistant

status-docker:
	docker-compose ps

clean-docker:
	@echo "$(RED)Clean up containers, images and volumes...$(NC)"
	docker-compose down --volumes --remove-orphans
	docker system prune -f

backup:
	@echo "$(YELLOW)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/backup-$$(date +%Y%m%d_%H%M%S).tar.gz docker/volumes/
	@echo "$(GREEN)New backup in backups/$(NC)"

restore:
	@if [ -z "$(BACKUP_FILE)" ]; then echo "$(RED)Please, provide BACKUP_FILE=path/to/backup.tar.gz$(NC)"; exit 1; fi
	@echo "$(YELLOW)Restoring from $(BACKUP_FILE)...$(NC)"
	docker-compose down
	@rm -rf docker/volumes/
	@tar -xzf $(BACKUP_FILE)
	@echo "$(GREEN)Restore done!$(NC)"

install:
	@if command -v pdm > /dev/null; then pdm install; else echo "$(RED)Pdm not installed. Please install it following instructions here: https://pdm-project.org$(NC)"; fi

test:
	@if command -v pdm > /dev/null; then pdm run pytest tests; else echo "$(RED)Pdm not installed. Please install it following instructions here: https://pdm-project.org$(NC)"; fi

run:
	@if command -v pdm > /dev/null; then pdm run python src/lurchhome/main.py; else echo "$(RED)Pdm not installed. Please install it following instructions here: https://pdm-project.org$(NC)"; fi

run-debug:
	@if command -v pdm > /dev/null; then pdm run python src/lurchhome/main.py --log DEBUG; else echo "$(RED)Pdm not installed. Please install it following instructions here: https://pdm-project.org$(NC)"; fi