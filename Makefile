.PHONY: help

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

build:
	@echo "$(YELLOW)Building services...$(NC)"
	docker-compose build

up:
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d

down:
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down

restart:
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose restart

logs:
	docker-compose logs -f

logs-ha:
	docker-compose logs -f homeassistant

status:
	docker-compose ps

clean:
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
	@if command -v pipenv > /dev/null; then pipenv install; else echo "$(RED)pipenv not installed. Please install it using: pip install pipenv$(NC)"; fi

install-dev:
	@if command -v pipenv > /dev/null; then pipenv install --dev; else echo "$(RED)pipenv not installed. Please install it using: pip install pipenv$(NC)"; fi

shell:
	pipenv shell

test:
	@if command -v pipenv > /dev/null; then pipenv run pytest tests/; else echo "$(RED)pipenv not installed. Please install it using: pip install pipenv$(NC)"; fi

lint:
	@if command -v pipenv > /dev/null; then \
		pipenv run flake8 src/ || echo "$(YELLOW)flake8 not configured$(NC)"; \
		pipenv run black --check src/ || echo "$(YELLOW)black not configured$(NC)"; \
	else echo "$(RED)pipenv not installed. Please install it using: pip install pipenv$(NC)"; fi

format:
	@if command -v pipenv > /dev/null; then pipenv run black src/; else echo "$(RED)pipenv not installed. Please install it using: pip install pipenvo$(NC)"; fi

run:
	@if command -v pipenv > /dev/null; then pipenv run python src/main.py; else echo "$(RED)pipenv not installed. Please install it using: pip install pipenv$(NC)"; fi