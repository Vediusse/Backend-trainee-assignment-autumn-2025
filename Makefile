.PHONY: install run test lint format clean docker-up docker-down docker-build


install:
	poetry install


run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload


test:
	poetry run pytest


lint:
	poetry run ruff check app tests
	poetry run black --check app tests


format:
	poetry run black app tests
	poetry run ruff check --fix app tests


clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +


docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

docker-build:
	docker-compose build