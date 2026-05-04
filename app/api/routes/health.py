from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.deps import db_session_dependency


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session=Depends(db_session_dependency)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
