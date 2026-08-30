# Storm Cases - Telegram Mini App

Telegram бот с Mini App для открытия кейсов, торговли предметами и социального взаимодействия.

## 🚀 Возможности

### Основные функции:
- 🎰 **Система кейсов** - открывайте кейсы разной редкости (обычные, редкие, легендарные)
- 📦 **Инвентарь и крафтинг** - управляйте предметами, создавайте новые из существующих
- 💰 **Рынок** - торговля между игроками, аукционы
- 💬 **Чат** - общение в реальном времени с сообществом
- ⚙️ **Настройки** - профиль, техподдержка, ежедневные награды

### Админ функции:
- 👥 **Управление участниками** - мут, бан, выдача валюты
- 📋 **Логи активности** - отслеживание действий пользователей
- 🎧 **Техподдержка** - ответы на запросы пользователей
- 💰 **Экономика** - управление курсами валют, промокоды
- 📊 **Аналитика** - статистика и отчеты
- 🛡️ **Модерация** - управление жалобами и контентом

## 📋 Требования

- Node.js 18+
- PostgreSQL 12+
- Redis (опционально, для кэширования)
- Telegram Bot Token

## 🔧 Установка

### 1. Клонирование и установка зависимостей

```bash
# Backend
cd storm-cases/backend
npm install

# Frontend
cd storm-cases/frontend
npm install
```

### 2. Настройка переменных окружения

Создайте файл `.env` в `backend/`:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# Server
PORT=3000
NODE_ENV=development

# Database
DATABASE_URL="postgresql://user:password@localhost:5432/stormcases"
REDIS_URL="redis://localhost:6379"

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-this
JWT_EXPIRES_IN=7d

# Admin
ADMIN_PASSWORD=your-admin-password
ADMIN_IDS=123456789,987654321

# Mini App
MINI_APP_URL=http://localhost:5173
```

### 3. Настройка базы данных

```bash
cd storm-cases/backend

# Генерация Prisma Client
npm run prisma:generate

# Создание миграций
npm run prisma:migrate

# Заполнение тестовыми данными
npm run prisma:seed
```

### 4. Запуск проекта

```bash
# Backend (терминал 1)
cd storm-cases/backend
npm run dev

# Frontend (терминал 2)
cd storm-cases/frontend
npm run dev
```

## 🌐 Развертывание

### Backend

1. Разверните PostgreSQL базу данных
2. Установите зависимости: `npm install`
3. Настройте переменные окружения
4. Запустите миграции: `npm run prisma:migrate`
5. Заполните данными: `npm run prisma:seed`
6. Соберите проект: `npm run build`
7. Запустите: `npm start`

### Frontend

1. Установите зависимости: `npm install`
2. Соберите проект: `npm run build`
3. Разверните `dist/` папку на статический хостинг

### Telegram Bot

1. Установите webhook:
```bash
curl -F "url=https://your-domain.com/webhook" \
  https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

## 📁 Структура проекта

```
storm-cases/
├── backend/
│   ├── src/
│   │   ├── bot/           # Telegram бот
│   │   ├── config/        # Конфигурация
│   │   ├── controllers/   # Контроллеры
│   │   ├── middleware/    # Middleware
│   │   ├── models/        # Модели данных
│   │   ├── routes/        # API маршруты
│   │   ├── services/      # Бизнес-логика
│   │   ├── types/         # TypeScript типы
│   │   ├── utils/         # Утилиты
│   │   └── index.ts       # Точка входа
│   ├── prisma/
│   │   ├── schema.prisma  # Схема БД
│   │   └── seed.ts        # Тестовые данные
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── pages/         # Страницы Mini App
│   │   ├── components/    # React компоненты
│   │   ├── utils/         # Утилиты
│   │   ├── App.tsx        # Главный компонент
│   │   └── main.tsx       # Точка входа
│   └── package.json
└── README.md
```

## 🔑 Telegram Bot Token

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте токен и добавьте в `.env`

## 🎮 Использование

1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Нажмите на кнопку "Открыть Storm Cases"
4. Используйте Mini App для открытия кейсов, торговли и общения

## 👨‍💻 Админ панель

1. Откройте настройки в Mini App
2. Перейдите во вкладку "Админ панель"
3. Введите админ пароль (из `.env`)
4. Получите доступ к функциям управления

## 🛠️ API Документация

### Authentication
- `POST /api/auth/admin-login` - Вход в админ панель
- `GET /api/auth/verify` - Проверка токена

### Users
- `GET /api/users/profile` - Профиль пользователя
- `PUT /api/users/profile` - Обновление профиля
- `POST /api/users/daily-reward` - Ежедневная награда
- `POST /api/users/refer` - Реферальная система

### Cases
- `GET /api/cases` - Список кейсов
- `GET /api/cases/:id` - Детали кейса
- `POST /api/cases/:id/open` - Открыть кейс
- `POST /api/cases/battle` - Боевой режим

### Inventory
- `GET /api/inventory` - Инвентарь
- `POST /api/inventory/craft` - Крафтинг
- `POST /api/inventory/upgrade` - Апгрейд предмета
- `PUT /api/inventory/:id/favorite` - Избранное

### Market
- `GET /api/market/listings` - Список объявлений
- `POST /api/market/list` - Создать объявление
- `POST /api/market/buy/:id` - Купить предмет
- `DELETE /api/market/listings/:id` - Удалить объявление
- `POST /api/market/auctions/:id/bid` - Ставка на аукционе

### Chat
- `GET /api/chat/history` - История чата
- `POST /api/chat/report` - Пожаловаться на сообщение
- `GET /api/chat/online` - Онлайн пользователи
- `POST /api/chat/:id/react` - Реакция на сообщение

### Support
- `GET /api/support/tickets` - Тикеты пользователя
- `POST /api/support/tickets` - Создать тикет
- `POST /api/support/tickets/:id/respond` - Ответить на тикет
- `GET /api/support/tickets/:id` - Детали тикета
- `PUT /api/support/tickets/:id/close` - Закрыть тикет

### Admin
- `GET /api/admin/users` - Список пользователей
- `GET /api/admin/users/:id` - Детали пользователя
- `PUT /api/admin/users/:id/mute` - Мьют пользователя
- `PUT /api/admin/users/:id/unmute` - Размьют
- `PUT /api/admin/users/:id/ban` - Бан пользователя
- `PUT /api/admin/users/:id/unban` - Разбан
- `PUT /api/admin/users/:id/balance` - Выдать баланс
- `GET /api/admin/logs` - Логи системы
- `GET /api/admin/support/tickets` - Тикеты поддержки
- `POST /api/admin/support/tickets/:id/respond` - Ответ на тикет
- `GET /api/admin/economy/rates` - Курсы валют
- `POST /api/admin/economy/promocodes` - Создать промокод
- `GET /api/admin/analytics/stats` - Статистика
- `GET /api/admin/moderation/reports` - Жалобы

## 🧪 Тестирование

```bash
# Backend тесты
cd backend
npm test

# Frontend тесты
cd frontend
npm test
```

## 📝 Лицензия

MIT

## 🤝 Поддержка

Для вопросов и поддержки используйте техподдержку в Mini App или создайте issue в репозитории.