# Vedo Calculator - MVP Веб-приложение

Система автоматического расчёта параметров изделий с распределением по отсечкам.

## Возможности

- **Авторизация пользователей** с JWT токенами и httpOnly cookies
- **Обработка файлов** в форматах `.txt` и `.xlsx`
- **Автоматический расчёт** отсечек, развёрток и площадей
- **Управление пользователями** для администраторов
- **Автоматическое удаление** файлов старше 7 дней
- **Логирование** всех операций

## Требования

- Python 3.14+
- Docker и Docker Compose (для контейнерного развёртывания)

## Установка и запуск

### Вариант 1: С помощью Docker (рекомендуется)

1. **Клонирование репозитория**
```bash
git clone <repository-url>
cd vedo-calculator
```

2. **Создание .env файла**
```bash
cp .env.example .env
```

Отредактируйте `.env` файл и обязательно измените `SECRET_KEY`:
```bash
SECRET_KEY=your-very-secret-and-random-key-here
```

3. **Запуск с помощью Docker Compose**
```bash
docker-compose up -d
```

4. **Доступ к приложению**
Откройте браузер: http://localhost

5. **Вход в систему**
- Логин: `admin` (или значение из `ADMIN_USERNAME`)
- Пароль: `adminpass` (или значение из `ADMIN_PASSWORD`)

### Вариант 2: Без Docker (локальная разработка)

1. **Создание виртуального окружения**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. **Установка зависимостей**
```bash
pip install -r requirements.txt
```

3. **Создание .env файла**
```bash
cp .env.example .env
```

4. **Запуск приложения**
```bash
cd backend
python -m uvicorn app.main:app --reload --host localhost --port 8035
```

5. **Доступ к приложению**
Откройте браузер: http://localhost:8035

## Структура проекта

```
vedo-calculator/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes/
│       │       ├── auth.py       # Маршруты авторизации
│       │       ├── files.py      # Маршруты работы с файлами
│       │       └── admin.py      # Админ-маршруты
│       ├── core/
│       │   ├── config.py         # Конфигурация
│       │   ├── database.py       # База данных
│       │   ├── security.py       # Безопасность (JWT, bcrypt)
│       │   └── dependencies.py   # Зависимости FastAPI
│       ├── models/
│       │   └── models.py         # SQLAlchemy модели
│       ├── services/
│       │   ├── calculator.py     # Логика обработки файлов
│       │   ├── scheduler.py      # Планировщик задач
│       │   └── init_admin.py     # Инициализация админа
│       └── main.py               # Точка входа FastAPI
├── static/
│   ├── index.html                # HTML интерфейс
│   ├── styles.css                # Стили
│   └── app.js                    # JavaScript логика
├── storage/                      # Хранилище файлов (создаётся автоматически)
├── logs/                         # Логи (создаётся автоматически)
├── Dockerfile                    # Docker образ
├── docker-compose.yml            # Docker Compose конфигурация
├── nginx.conf                    # Конфигурация Nginx
├── requirements.txt              # Python зависимости
├── .env.example                  # Пример конфигурации
└── README.md                     # Документация
```

## Роли пользователей

### Администратор (`admin`)
- Создание, редактирование и удаление пользователей
- Просмотр всех файлов в системе
- Загрузка и обработка файлов

### Пользователь (`user`)
- Загрузка и обработка файлов
- Просмотр только своих файлов
- Скачивание и удаление своих файлов

## API Эндпоинты

### Авторизация
- `POST /api/v1/auth/login` - Вход в систему
- `POST /api/v1/auth/logout` - Выход из системы
- `GET /api/v1/auth/me` - Получение текущего пользователя

### Файлы
- `POST /api/v1/files/upload` - Загрузка файла
- `GET /api/v1/files/list` - Список файлов (с пагинацией)
- `GET /api/v1/files/download/{file_id}` - Скачивание файла
- `DELETE /api/v1/files/{file_id}` - Удаление файла

### Администрирование
- `POST /api/v1/admin/users` - Создание пользователя
- `GET /api/v1/admin/users` - Список пользователей (с пагинацией)
- `PUT /api/v1/admin/users/{user_id}` - Обновление пользователя
- `DELETE /api/v1/admin/users/{user_id}` - Удаление пользователя

## Настройка конфигурации

Все настройки определяются в `.env` файле:

### Безопасность
```env
SECRET_KEY=your-secret-key        # Ключ для JWT (обязательно измените!)
ACCESS_TOKEN_EXPIRE_HOURS=24      # Время жизни токена
```

### База данных
```env
# SQLite (по умолчанию)
DATABASE_URL=sqlite+aiosqlite:///./vedo.db

# PostgreSQL (для production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vedo_db
```

### Константы обработки
```env
FORM_CAPACITY_1=4                 # Вместимость формы типа 1
FORM_CAPACITY_2=5                 # Вместимость формы типа 2
FORM_CAPACITY_3=6                 # Вместимость формы типа 3
CUTOFF_TYPE_1=8                   # Тип отсечки для формы 1
CUTOFF_TYPE_2=9                   # Тип отсечки для формы 2
CUTOFF_TYPE_3=10                  # Тип отсечки для формы 3
```

## Миграция на PostgreSQL

Для перехода с SQLite на PostgreSQL:

1. Установите PostgreSQL
2. Создайте базу данных
3. Обновите `DATABASE_URL` в `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vedo_db
```
4. Перезапустите приложение

## Логирование

Логи сохраняются в `logs/app.log` с автоматической ротацией:
- Размер файла: 10 МБ
- Количество файлов: 5
- Формат: `timestamp - logger - level - message`

Логируются:
- Успешные/неудачные входы
- Загрузка и удаление файлов
- Создание/изменение пользователей
- Ошибки обработки

## Автоматическое удаление файлов

Планировщик задач автоматически удаляет файлы старше 7 дней:
- Запуск: каждый день в 3:00 ночи
- Настройка: `FILE_RETENTION_DAYS` в `.env`

## Безопасность

- JWT токены с временем жизни 24 часа
- httpOnly cookies для защиты от XSS
- Bcrypt для хеширования паролей
- Ограничение размера файлов (20 МБ)
- Защита эндпоинтов по ролям
- Валидация входных данных

## Отладка

Для включения режима разработки:
```env
ENVIRONMENT=development
```

В этом режиме:
- Детальное логирование SQL запросов
- Hot reload при изменении кода
- Расширенные логи ошибок

---

**Vedo Calculator v1.0.0** - Система автоматического расчёта для строительной отрасли
