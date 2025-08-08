.PHONY: dev build stop clean setup migrate shell logs frontend-logs backend-logs

# One-command development setup
dev: setup build
	docker-compose up

# Production setup
prod: setup
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d

# Production stop
prod-stop:
	docker-compose -f docker-compose.prod.yml down

# Production logs
prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

# Setup environment files
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env file and add your OPENAI_API_KEY"; \
	fi
	@if [ ! -f backend/requirements.txt ]; then \
		echo "⚠️  Please run 'make init-backend' first"; \
	fi
	@if [ ! -f frontend/package.json ]; then \
		echo "⚠️  Please run 'make init-frontend' first"; \
	fi

# Build all containers
build:
	docker-compose build

# Stop all services
stop:
	docker-compose down

# Clean everything (containers, volumes, images)
clean:
	docker-compose down -v --rmi all

# Django management commands
migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

shell:
	docker-compose exec web python manage.py shell

createsuperuser:
	docker-compose exec web python manage.py createsuperuser

# Logs
logs:
	docker-compose logs -f

frontend-logs:
	docker-compose logs -f frontend

backend-logs:
	docker-compose logs -f web

# Initialize backend structure
init-backend:
	mkdir -p backend
	cd backend && django-admin startproject mini_guru .
	@echo "Backend structure created!"

# Initialize frontend structure  
init-frontend:
	mkdir -p frontend
	cd frontend && npx create-next-app@14 . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
	@echo "Frontend structure created!"

# Development helpers
install-backend:
	docker-compose exec web pip install -r requirements.txt

install-frontend:
	docker-compose exec frontend npm install

# Database helpers
db-reset:
	docker-compose down
	docker volume rm mini_guru_postgres_data
	docker-compose up -d postgres
	sleep 5
	make migrate

# Backup database
db-backup:
	docker-compose exec postgres pg_dump -U postgres mini_guru > backup_$(shell date +%Y%m%d_%H%M%S).sql