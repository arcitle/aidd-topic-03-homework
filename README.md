# Investing Demo

Django-приложение для просмотра каталога акций, котировок и графиков.
Хранилище — PostgreSQL, брокер фоновых задач — Redis, периодическое обновление
цен выполняют Celery worker и beat. Рыночные данные — T-Tech Invest API
(пакет `t-tech-investments`, преемник `tinkoff-investments`).

## Быстрый старт (Docker)

```sh
cp .env.example .env   # при необходимости задайте TINKOFF_TOKEN
docker compose up --build
```

Сервисы: PostgreSQL, Redis, веб-приложение на http://localhost:8000,
Celery worker и beat. Миграции применяются при старте `web`.

Загрузка каталога акций (нужен `TINKOFF_TOKEN`):

```sh
docker compose exec web python manage.py add_shares
```

## Локальная разработка (venv + Docker для инфраструктуры)

Поднимите только БД и Redis:

```sh
docker compose up -d db redis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

В отдельных терминалах (с активированным `.venv`):

```sh
celery -A config worker -l info
celery -A config beat -l info
```

## API и проверки

- Веб UI: `/`
- REST API: `/api/v1/shares/`
- Тесты: `python manage.py test`
