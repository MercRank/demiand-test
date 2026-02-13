.PHONY: help build up down restart logs clean install test

help:
	@echo "Доступные команды:"
	@echo "  make build      - Сборка Docker образов"
	@echo "  make up         - Запуск всех сервисов"
	@echo "  make down       - Остановка всех сервисов"
	@echo "  make restart    - Перезапуск всех сервисов"
	@echo "  make logs       - Просмотр логов"
	@echo "  make clean      - Очистка Docker ресурсов"
	@echo "  make install    - Локальная установка зависимостей"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-bot:
	docker compose logs -f bot

logs-admin:
	docker compose logs -f admin

logs-qdrant:
	docker compose logs -f qdrant

clean:
	docker compose down -v
	docker system prune -f

install:
	pip install -r requirements.txt

dev-bot:
	python -m src.bot.main

dev-admin:
	streamlit run src/admin/app.py
