# Investing Demo

Django-приложение для просмотра каталога акций, котировок и графиков. Хранилище — PostgreSQL, брокер фоновых задач — Redis, периодическое обновление выполняют Celery worker и beat. Для рыночных данных используется клиент T-Tech Invest.

## Запуск всего приложения в Docker

Нужен установленный Docker с работающим Docker daemon и Compose plugin. Не устанавливайте зависимости Python на хост:

```sh
docker compose up --build
```

Compose поднимет PostgreSQL, Redis, веб-приложение на <http://localhost:8000>, Celery worker и beat. При первом запуске веб-контейнер применит миграции автоматически. Без `TINKOFF_TOKEN` каталог, API и прочие страницы доступны, а график будет пустым; для импорта акций и обновления котировок задайте токен в `.env`.

Переменные окружения можно задать в `.env` (пример):

```dotenv
TINKOFF_TOKEN=your-token
DJANGO_SECRET_KEY=replace-with-a-random-secret
POSTGRES_PASSWORD=replace-this-password
```

Веб-приложение доступно на `/`, REST API — на `/api/v1/shares/`. Каталог можно заполнить из терминала контейнера:

```sh
docker compose exec web python manage.py add_shares
```

Для локальной разработки без контейнера требуется активировать виртуальное окружение и запустить PostgreSQL и Redis с теми же параметрами подключения, затем выполнить `python manage.py migrate` и `python manage.py runserver`.
