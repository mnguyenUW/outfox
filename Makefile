.PHONY: help setup run test clean

help:
	@echo "Available commands:"
	@echo "  make setup    - Set up the development environment"
	@echo "  make run      - Run the application with Docker"
	@echo "  make test     - Run tests"
	@echo "  make etl      - Run ETL script"
	@echo "  make clean    - Clean up containers and volumes"

setup:
	cp .env.example .env
	docker-compose build

run:
	docker-compose up

run-detached:
	docker-compose up -d

stop:
	docker-compose down

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	docker-compose exec app pytest tests/ -v

etl:
	docker-compose exec app python -m etl.etl

logs:
	docker-compose logs -f

shell-db:
	docker-compose exec postgres psql -U postgres -d healthcare_db

shell-app:
	docker-compose exec app /bin/bash

format:
	docker-compose exec app black .
	docker-compose exec app isort .