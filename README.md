# Professional Dietologist

Telegram nutrition assistant with FastAPI admin backend, aiogram bot worker, PostgreSQL, SQLAlchemy, Alembic, and multi-provider AI fallback.

## Run

Web:

```bash
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Worker:

```bash
alembic upgrade head
python -m app.bot.runner
```
