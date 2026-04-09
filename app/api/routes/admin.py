from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import db_session_dependency, require_admin
from app.config import get_settings
from app.db.enums import UserStatus
from app.repositories.admin import AdminRepository
from app.repositories.meals import MealRepository
from app.repositories.users import UserRepository
from app.services.access import AccessService


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(get_settings().templates_dir))


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    users = await UserRepository().list_users(session, limit=50)
    pending_requests = await UserRepository().list_pending_access_requests(session, limit=50)
    meals = await MealRepository().list_recent_meals(session, limit=50)
    admin_repo = AdminRepository()
    ai_logs = await admin_repo.list_recent_ai_logs(session, limit=50)
    reminder_logs = await admin_repo.list_recent_notification_logs(session, limit=50)
    models = await admin_repo.list_model_registry(session)
    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "request": request,
            "users": users,
            "pending_requests": pending_requests,
            "meals": meals,
            "ai_logs": ai_logs,
            "reminder_logs": reminder_logs,
            "models": models,
        },
    )


@router.post("/access-requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    await AccessService(get_settings()).approve_request(session, request_id, None)
    await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/access-requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    await AccessService(get_settings()).reject_request(
        session, request_id, None, "Rejected from admin panel"
    )
    await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    reason: str = Form(default="Blocked from admin panel"),
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    user = await UserRepository().get_by_id(session, user_id)
    if user is not None:
        await AdminRepository().block_user(session, user, reason, None)
        await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    user = await UserRepository().get_by_id(session, user_id)
    if user is not None:
        await AdminRepository().unblock_user(session, user)
        await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/models/{model_id}")
async def update_model(
    model_id: int,
    is_active: str = Form(default="false"),
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    entry = await AdminRepository().get_model_registry_entry(session, model_id)
    if entry is not None:
        await AdminRepository().toggle_model_registry_entry(session, entry, is_active == "true")
        await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/meals/{meal_id}/correct")
async def correct_meal(
    meal_id: int,
    corrected_summary: str = Form(...),
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    meal = await MealRepository().get_meal_entry(session, meal_id)
    if meal is not None and meal.analysis_result is not None:
        meal.analysis_result.corrected_summary = corrected_summary
        await session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    _: str = Depends(require_admin),
    session=Depends(db_session_dependency),
):
    user = await UserRepository().get_by_id(session, user_id)
    if user is not None:
        user.status = UserStatus.REJECTED
        await session.commit()
    return RedirectResponse("/admin", status_code=303)
