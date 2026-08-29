# STORM CASES - Telegram Bot

Telegram-бот для открытия кейсов с WebApp интерфейсом.

## 📋 Описание проекта

STORM CASES — это полноценный Telegram-бот с WebApp интерфейсом, который позволяет пользователям:
- Открывать кейсы и получать предметы разной редкости
- Торговать предметами на рынке
- Участвовать в PvP матчах
- Выполнять квесты и получать достижения
- Использовать колесо фортуны и слоты
- Создавать кланы и общаться в чате
- Пополнять баланс через различные способы оплаты

## 🚀 Установка и запуск

### Требования
- Python 3.10+
- pip

### Шаг 1: Клонирование и установка зависимостей

```bash
cd storm-cases
pip install -r requirements.txt
```

### Шаг 2: Настройка переменных окружения

Файл `.env` уже создан с вашими настройками:
- `BOT_TOKEN`: Токен вашего Telegram бота (уже установлен)
- `ADMIN_TELEGRAM_ID`: Ваш Telegram ID для админ-прав (8601398572)
- `DATABASE_URL`: URL базы данных (по умолчанию SQLite)
- `WEBAPP_URL`: URL для WebApp (по умолчанию http://localhost:8000)

### Шаг 3: Запуск

Запуск API сервера (FastAPI):
```bash
python main.py
```

Запуск Telegram бота (в отдельном терминале):
```bash
python Bot.py
```

## 📁 Структура проекта

```
storm-cases/
├── .env                    # Переменные окружения
├── .env.example            # Пример переменных окружения
├── config.py               # Конфигурация
├── database.py             # Настройка базы данных
├── models.py               # Модели базы данных
├── main.py                 # FastAPI backend
├── Bot.py                  # Telegram бот
├── payments.py             # Интеграция платежей
├── requirements.txt        # Зависимости Python
├── index.html              # WebApp интерфейс
└── README.md               # Этот файл
```

## 🎮 Команды бота

- `/start` — Запустить бота и открыть WebApp
- `/help` — Помощь
- `/profile` — Профиль пользователя
- `/balance` — Проверить баланс
- `/servers` — Список серверов

### Админ-команды (только для админа)

- `/admin` — Панель администратора
- `/admin_users` — Список пользователей
- `/admin_stats` — Статистика сервера
- `/admin_addcoins <user_id> <amount>` — Добавить монеты пользователю
- `/admin_broadcast <message>` — Отправить рассылку

## 💰 Система платежей

### Telegram Stars
- 10 ⭐ = 500 монет
- 50 ⭐ = 3000 монет
- 100 ⭐ = 10000 монет
- 500 ⭐ = 60000 монет

### Криптовалюта (USDT TRC20)
- Интеграция с Crypto Pay API (опционально)

### Банковская карта
- Интеграция с платежными шлюзами (YooKassa, UnitPay и др.)

## 🎨 Редкость предметов

- ⚪ **Common** (Обычный) — базовая цена 50 монет
- 🔵 **Rare** (Редкий) — базовая цена 150 монет
- 🟣 **Epic** (Эпический) — базовая цена 400 монет
- 🟡 **Legendary** (Легендарный) — базовая цена 1000 монет
- 🔴 **Mythic** (Мифический) — базовая цена 3000 монет

## 🔧 API Эндпоинты

### Публичные
- `GET /` — WebApp интерфейс
- `POST /api/register` — Регистрация пользователя
- `GET /api/state` — Получение состояния пользователя
- `GET /api/servers` — Список серверов

### Действия (POST /api/action)
- `change_server` — Сменить сервер
- `open_case` — Открыть кейс
- `sell_item` — Продать предмет
- `list_market` — Выставить на рынок
- `buy_market` — Купить с рынка
- `cancel_listing` — Снять с рынка
- `send_chat` — Отправить сообщение в чат
- `craft` — Крафт предмета
- `buy_subscription` — Купить подписку
- `send_gift` — Отправить подарок
- `spin_wheel` — Крутить колесо
- `spin_slots` — Крутить слоты
- `start_pvp` — Начать PvP матч
- `claim_daily` — Получить ежедневную награду
- `claim_quest` — Получить награду за квест
- `activate_promo` — Активировать промокод
- И многие другие...

## 🛡️ Безопасность

- Telegram WebApp initData проверяется на сервере
- Админ-команды доступны только для указанного ADMIN_TELEGRAM_ID
- Все транзакции записываются в историю

## 📊 База данных

Используется SQLAlchemy ORM с поддержкой асинхронных операций. По умолчанию используется SQLite, но можно легко переключиться на PostgreSQL или MySQL.

### Основные таблицы:
- `users` — Пользователи
- `servers` — Серверы
- `cases` — Кейсы
- `items` — Предметы
- `inventory_items` — Инвентарь
- `market_listings` — Рынок
- `chat_messages` — Чат
- `quests` — Квесты
- `achievements` — Достижения
- И многие другие...

## 🚀 Развертывание

### Использование Docker (опционально)

Создайте `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Использование systemd (Linux)

Создайте файл сервиса `/etc/systemd/system/storm-cases-api.service`:
```ini
[Unit]
Description=STORM CASES API
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/storm-cases
ExecStart=/usr/bin/python3 /path/to/storm-cases/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🐛 Устранение проблем

### Бот не отвечает
- Проверьте, что BOT_TOKEN правильный в .env
- Убедитесь, что бот запущен (`python Bot.py`)
- Проверьте логи на наличие ошибок

### WebApp не открывается
- Убедитесь, что API сервер запущен (`python main.py`)
- Проверьте, что WEBAPP_URL в .env правильный
- Проверьте, что порт 8000 не занят

### Ошибки базы данных
- Удалите файл `storm_cases.db` для пересоздания базы
- Проверьте права доступа к файлу базы данных

## 📝 Лицензия

Этот проект создан для образовательных целей.

## 👤 Автор

Создано с помощью ИИ-разработчика для Telegram бота STORM CASES.

## 📞 Поддержка

Для связи и поддержки используйте функцию "Поддержка" в приложении или обратитесь к администратору.
