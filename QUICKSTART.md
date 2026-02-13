# 🚀 Быстрый старт

Запуск проекта за 3 минуты.

## 📋 Что нужно

1. **Docker** и **Docker Compose**
2. **OpenAI API ключ** → [platform.openai.com](https://platform.openai.com)
3. **Telegram Bot Token** → [@BotFather](https://t.me/BotFather)

## ⚡ Запуск

### 1. Клонируйте репозиторий

```bash
git clone <your-repo-url>
cd <project-folder>
```

### 2. Создайте .env файл

```bash
cp .env.example .env
nano .env
```

Заполните:
```env
OPENAI_API_KEY=sk-proj-ваш-ключ
TELEGRAM_BOT_TOKEN=ваш-токен
```

### 3. Запустите всё одной командой

```bash
docker compose up -d --build
```

### 4. Загрузите данные

1. Откройте: http://localhost:8501
2. Загрузите Excel файл
3. Нажмите "Обработать файл"

### 5. Проверьте бота

Напишите `/start` вашему боту в Telegram.

## ✅ Готово!

Бот работает и отвечает на вопросы.

## 🔧 Полезные команды

```bash
# Логи бота
docker compose logs -f bot

# Логи админки
docker compose logs -f admin

# Перезапуск
docker compose restart

# Остановка
docker compose down
```

## 📖 Документация

- [README.md](README.md) — полная документация
- [DEPLOY.md](DEPLOY.md) — деплой на VPS
- [CHANGELOG.md](CHANGELOG.md) — история изменений

## 🆘 Проблемы?

### Бот не отвечает
```bash
docker compose logs bot
```

### Админка не открывается
```bash
docker compose ps
docker compose logs admin
```

### Qdrant не работает
```bash
docker compose restart qdrant
docker compose logs qdrant
```

---

Детали в [README.md](README.md)
