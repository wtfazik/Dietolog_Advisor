from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse


router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    runtime = getattr(request.app.state, "telegram_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram runtime is not initialized",
        )
    if not runtime.schema_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database schema is not ready",
        )

    update = await request.json()
    await runtime.dispatcher.feed_webhook_update(runtime.bot, update)
    return JSONResponse({"ok": True})
