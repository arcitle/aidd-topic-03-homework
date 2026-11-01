# ANALYSIS.md — Анализ исходного кода Investing Demo

## 1. Назначение приложения и технологический стек

### Назначение

**Investing Demo** — веб-приложение для просмотра и управления справочником акций (инструментов фондового рынка). Приложение:

- хранит список акций в собственной БД;
- отображает котировки и направление изменения цены;
- показывает исторический график цены по данным внешнего API;
- позволяет авторизованным пользователям создавать, редактировать и удалять записи об акциях;
- предоставляет REST API для CRUD-операций над акциями;
- периодически обновляет последние цены через фоновые задачи.

Рыночные данные запрашиваются из **Tinkoff Invest API**.

### Технологический стек

| Слой | Технологии |
|------|------------|
| Backend | Python, Django 4.1.7 |
| API | Django REST Framework 3.14, django-filter |
| ORM / БД | Django ORM, PostgreSQL (`psycopg2-binary`) |
| Фоновые задачи | Celery 5.2, Redis (брокер) |
| Внешний рынок | `tinkoff-investments` (gRPC-клиент Tinkoff Invest API) |
| Графики | Plotly 5.13 |
| UI | Django Templates, Bootstrap 3 (`crispy-bootstrap3`, `django-crispy-forms`) |
| Инфраструктура | Docker Compose (PostgreSQL, Redis) |
| Форматирование кода | black, isort |

---

## 2. Структура проекта и основные компоненты

```
aidd-topic-03-homework/
├── manage.py                 # Точка входа Django
├── docker-compose.yml        # PostgreSQL + Redis
├── requirements.txt          # Зависимости Python
├── config/                   # Проект Django (настройки, URL, Celery)
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py / asgi.py
│   └── __init__.py           # Импорт celery_app при старте
├── dashboard/                # Основное приложение: акции, UI, API, задачи
│   ├── models.py             # Модель Share
│   ├── views.py              # CBV для веб-интерфейса
│   ├── forms.py              # ModelForm для Share
│   ├── urls.py
│   ├── admin.py
│   ├── tasks.py              # Celery-задача обновления цен
│   ├── services/
│   │   ├── market_data.py    # Последняя цена из Tinkoff
│   │   └── graph.py          # Построение графика свечей
│   ├── api/
│   │   └── v1/               # REST API v1 (ViewSet, serializer, router)
│   ├── management/commands/
│   │   └── add_shares.py     # Первичная загрузка акций из API
│   └── templates/dashboard/  # HTML-шаблоны
└── user/                     # Аутентификация и регистрация
    ├── views.py
    ├── forms.py
    ├── urls.py
    ├── models.py             # Обёртка над стандартным User
    └── templates/user/
```

### Назначение компонентов

| Компонент | Назначение |
|-----------|------------|
| `config` | Конфигурация Django/Celery, корневой роутинг, подключение к PostgreSQL и Redis |
| `dashboard` | Доменная логика акций: модели, веб-CRUD, REST API, интеграция с Tinkoff, фоновое обновление цен |
| `dashboard.services` | Изолированный слой работы с внешним API и визуализацией |
| `dashboard.api.v1` | Версионированный REST API (`/api/v1/shares`) |
| `dashboard.tasks` | Периодическое обновление `last_price` и `is_trend_high` |
| `user` | Регистрация, вход и выход пользователей (сессионная аутентификация Django) |

---

## 3. Архитектура и взаимодействие компонентов

Приложение построено по классической схеме **монолитного Django-проекта** с разделением на приложения (`dashboard`, `user`), слоем сервисов для внешних вызовов и асинхронным воркером Celery.

### Высокоуровневая схема

```
┌─────────────┐     HTTP      ┌──────────────────────┐
│  Браузер /  │ ────────────► │  Django (WSGI)       │
│  API-клиент │               │  config.urls         │
└─────────────┘               └──────────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             dashboard.views      dashboard.api.v1         user.views
             (HTML + CBV)         (DRF ViewSet)         (auth/reg/logout)
                    │                    │                    │
                    └──────────┬─────────┘                    │
                               ▼                              ▼
                        Share (ORM)                    django.contrib.auth
                               │                         (User + Session)
                               ▼
                          PostgreSQL
                               ▲
                               │
┌──────────────┐        ┌──────┴───────┐        ┌─────────────────┐
│ Celery Beat  │ ───►   │ Celery Worker│ ───►   │ Tinkoff Invest  │
│ (расписание) │        │ update_last_ │        │ API (gRPC)      │
└──────────────┘        │ price        │        └─────────────────┘
                        └──────┬───────┘
                               │
                          Redis broker
```

### Потоки взаимодействия

1. **Просмотр списка акций**  
   `GET /` → `ShareListView` → `Share.objects` → шаблон `list.html`. Доступен без аутентификации.

2. **Детальная страница с графиком**  
   `GET /<pk>` → `ShareDetailView` → чтение `Share` из БД → `get_graph(share)` → Tinkoff API (дневные свечи за 180 дней) → Plotly HTML → `detail.html`.

3. **CRUD акций (веб)**  
   Создание / изменение / удаление доступны только аутентифицированным пользователям (`IsUserAuthenticatedMixin`). Данные проходят через `ShareModelForm` и сохраняются в PostgreSQL.

4. **CRUD акций (API)**  
   ` /api/v1/shares/` → `ShareViewSet` (ModelViewSet) → `ShareSerializer` → ORM. Поддержаны фильтрация, поиск и сортировка. Ограничений доступа в ViewSet нет.

5. **Аутентификация**  
   Регистрация / вход / выход в приложении `user`. После успеха — redirect на список акций. Сессия хранится стандартным механизмом Django.

6. **Фоновое обновление цен**  
   Celery Beat ставит задачу `dashboard.tasks.update_last_price` (в коде интервал `10.0` секунд, имя расписания — «every-5-min»). Воркер для каждой акции вызывает `get_last_data`, сравнивает с прежней ценой и обновляет `last_price` / `is_trend_high`.

7. **Первичное наполнение**  
   Management-команда `python manage.py add_shares` загружает каталог акций из Tinkoff (`instruments.shares`) через `get_or_create`.

---

## 4. Библиотеки и внешние зависимости

### Основные runtime-зависимости

| Пакет | Роль |
|-------|------|
| `Django==4.1.7` | Веб-фреймворк |
| `djangorestframework==3.14.0` | REST API |
| `django-filter==22.1` | Фильтрация queryset в API |
| `django-crispy-forms`, `crispy-bootstrap3` | Рендеринг форм (Bootstrap 3) |
| `psycopg2-binary==2.9.5` | Драйвер PostgreSQL |
| `celery==5.2.7`, `redis==4.5.1`, `kombu`, `amqp`, `billiard`, `vine` | Очередь задач и брокер |
| `tinkoff-investments==0.2.0b50`, `tinkoff`, `grpcio`, `protobuf`, `pydantic` | Клиент Tinkoff Invest API |
| `plotly==5.13.1` | Построение интерактивных графиков |
| `cachetools`, `tenacity`, `python-dateutil` | Вспомогательные утилиты (в т.ч. транзитивно для SDK) |

### Инфраструктурные сервисы

- **PostgreSQL** — основная БД (`NAME=investing`, пользователь/пароль `postgres`, хост `localhost:5432`).
- **Redis** — брокер Celery (`redis://127.0.0.1:6379/0`).
- **Tinkoff Invest API** — внешний источник инструментов, последних цен и свечей; токен задаётся в `config.settings.TINKOFF_TOKEN`.

### Dev-зависимости

- `black`, `isort` — форматирование и сортировка импортов.

### Frontend (CDN / static)

- Bootstrap (локальные static CSS), jQuery, Popper, Font Awesome, Moment.js, Tempus Dominus, Plotly.js (CDN).

---

## 5. Модель данных

### Сущность `Share` (`dashboard.models.Share`)

Единственная доменная модель приложения. Связей с другими моделями проекта нет (нет ForeignKey / M2M).

| Атрибут | Тип | Ограничения / особенности |
|---------|-----|---------------------------|
| `id` | `BigAutoField` | Первичный ключ (по умолчанию Django) |
| `figi` | `CharField(255)` | Уникальный идентификатор инструмента Tinkoff |
| `isin` | `CharField(255)` | Международный код ценной бумаги |
| `name` | `CharField(255)` | Наименование компании |
| `ticker` | `CharField(10)` | Уникальный тикер |
| `currency` | `CharField(20)` | Валюта котировки |
| `uid` | `CharField(255)` | Уникальный UUID инструмента в Tinkoff |
| `last_price` | `FloatField` | Текущая цена; `null`/`blank` допустимы |
| `is_trend_high` | `BooleanField` | Признак роста цены относительно предыдущего значения; `null`/`blank` допустимы |
| `updated_at` | `DateTimeField(auto_now=True)` | Время последнего сохранения записи |

**Мета:** `verbose_name = "Акция"`, `verbose_name_plural = "Акции"`.

### Пользователи

Отдельной кастомной модели пользователя нет: `user.models` экспортирует `User = get_user_model()` (стандартный `django.contrib.auth.models.User`).

При регистрации email используется и как `username`, и как `email` (`User.objects.create_user(email, email, password)`). Явной связи `User` ↔ `Share` в схеме БД нет: авторизация влияет только на доступ к веб-CRUD.

### ER-схема (логическая)

```
┌──────────────────────────┐          ┌─────────────────────────┐
│ Share                    │          │ auth_user (Django)      │
├──────────────────────────┤          ├─────────────────────────┤
│ PK id                    │          │ PK id                   │
│ UQ figi                  │   нет    │ username (= email)      │
│    isin                  │──связи──►│ email                   │
│    name                  │          │ password                │
│ UQ ticker                │          │ …                       │
│    currency              │          └─────────────────────────┘
│ UQ uid                   │
│    last_price            │
│    is_trend_high         │
│    updated_at            │
└──────────────────────────┘
```

Исторические котировки в БД **не хранятся**: график строится «на лету» из ответа Tinkoff API.

---

## 6. Обработка пользовательских запросов и взаимодействие с БД

### Маршрутизация

Корневой `config/urls.py`:

| Префикс | Приложение |
|---------|------------|
| `/admin/` | Django Admin |
| `/` | `dashboard.urls` |
| `/user` | `user.urls` |

Веб-маршруты `dashboard`:

| URL | View | Операция с БД |
|-----|------|---------------|
| `GET /` | `ShareListView` | `SELECT` с пагинацией (100), сортировка по `name` |
| `GET /<pk>` | `ShareDetailView` | `Share.objects.get(id=pk)` + внешний API для графика |
| `GET/POST /create` | `ShareCreateView` | `INSERT` через ModelForm (только auth) |
| `GET/POST /update/<pk>` | `ShareUpdateView` | `UPDATE` через ModelForm (только auth) |
| `GET/POST /delete/<pk>` | `ShareDeleteView` | `DELETE` (только auth) |

API:

| URL | Handler | Операции |
|-----|---------|----------|
| `/api/v1/shares/` | `ShareViewSet` | list / create |
| `/api/v1/shares/<pk>/` | `ShareViewSet` | retrieve / update / partial_update / destroy |

Фильтры API: точное совпадение по `name`, `ticker`; поиск по `name` (`$name`); сортировка по `name`, `ticker`. Пагинация: LimitOffset, `PAGE_SIZE=100`.

Маршруты `user`:

| URL | Назначение |
|-----|------------|
| `/user/login/` | Вход |
| `/user/registration/` | Регистрация |
| `/user/logout/` | Выход |

### Механизм веб-запросов

1. Middleware Django обрабатывает сессию, CSRF, аутентификацию.
2. URLResolver направляет запрос в CBV.
3. Для мутаций `IsUserAuthenticatedMixin` проверяет `request.user.is_authenticated`; при отказе — redirect на `dashboard:index`.
4. CBV работают с ORM через generic views (`ListView`, `CreateView`, `UpdateView`, `DeleteView`) или явный `Share.objects.get`.
5. Ответ рендерится шаблонами Bootstrap; формы — через `ShareModelForm` / crispy.

### Механизм API-запросов

1. DRF `DefaultRouter` регистрирует ресурс `shares`.
2. `ModelViewSet` выполняет стандартный CRUD поверх `Share.objects.all()`.
3. `ShareSerializer` сериализует поля: `id`, `figi`, `isin`, `name`, `ticker`, `currency`, `last_price`, `is_trend_high`, `updated_at` (поле `uid` в API не отдаётся).
4. Запись в БД — через serializer/`Model.objects` (стандартный путь DRF).

### Взаимодействие с БД вне HTTP

- **Celery-задача `update_last_price`:** читает все `Share`, для каждой получает цену из Tinkoff и делает `Share.objects.filter(id=...).update(...)`.
- **Команда `add_shares`:** массовый `get_or_create` по данным `client.instruments.shares()`.
- **Django Admin:** CRUD через `ShareAdmin` с поиском по `figi`, `isin`, `name`, `ticker`.

### Интеграция с внешним API (сервисный слой)

| Функция | Файл | Запрос к Tinkoff | Использование результата |
|---------|------|------------------|--------------------------|
| `get_last_data(share)` | `market_data.py` | `market_data.get_last_prices(figi=...)` | Целое число `units` цены + timestamp → обновление БД |
| `get_graph(share)` | `graph.py` | `get_all_candles` (180 дней, дневной интервал) | Ряды дат/цен → Plotly `Scatter` → HTML-div |
| `add_shares` | management command | `instruments.shares()` | Создание записей `Share` в PostgreSQL |

Все вызовы используют `Client(TINKOFF_TOKEN)` в контексте `with`.

---

## Краткие выводы по архитектуре

1. Приложение — **монолитный Django-сервис** с двумя apps (`dashboard`, `user`), REST-слоем и фоновым обновлением котировок.
2. Доменная модель минимальна: одна сущность **`Share`** без связей; пользователи — стандартный Django User без привязки к акциям.
3. Источник истины по рыночным данным — **Tinkoff Invest API**; локальная БД кэширует справочник инструментов и последнюю цену.
4. Разделение ответственности в целом ясное: views → ORM/forms; services → внешний API; tasks → периодическая синхронизация; api.v1 → программный доступ.
5. Веб-CRUD защищён проверкой аутентификации; REST API и чтение списка/деталей — открыты (в текущей реализации без permission-классов).
