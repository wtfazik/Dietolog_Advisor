from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import admin, health
from app.config import get_settings
from app.db.session import SessionLocal
from app.logging import configure_logging
from app.services.model_registry import ModelRegistryService


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings = get_settings()
    async with SessionLocal() as session:
        await ModelRegistryService(settings).seed_defaults(session)
        await session.commit()
    yield


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(health.router)
app.include_router(admin.router)


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/admin")
