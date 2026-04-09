from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import admin, health, telegram
from app.bot.webhook import start_telegram_runtime, stop_telegram_runtime
from app.config import get_settings
from app.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    runtime = await start_telegram_runtime(settings)
    app.state.telegram_runtime = runtime
    yield
    await stop_telegram_runtime(runtime)


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(telegram.router)


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/admin")
