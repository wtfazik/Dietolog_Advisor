from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse


router = APIRouter(tags=["telegram"])
logger = logging.getLogger(__name__)


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    runtime = getattr(request.app.state, "telegram_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram runtime is not initialized",
        )

    update = await request.json()
    try:
        await runtime.dispatcher.feed_webhook_update(runtime.bot, update)
    except Exception:
        logger.exception("Telegram webhook update processing failed")
    return JSONResponse({"ok": True})
