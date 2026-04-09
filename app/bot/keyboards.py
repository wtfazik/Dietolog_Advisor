from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import t


def access_request_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(locale, "access_request_button"), callback_data="access:request")
    return builder.as_markup()


def disclaimer_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(locale, "accept_disclaimer"), callback_data="onboarding:accept_disclaimer")
    return builder.as_markup()


def main_menu_keyboard(locale: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [
        (t(locale, "menu_analyze_meal"), "menu:analyze_meal"),
        (t(locale, "menu_meal_plan"), "menu:meal_plan"),
        (t(locale, "menu_question"), "menu:question"),
        (t(locale, "menu_reminders"), "menu:reminders"),
        (t(locale, "menu_reports"), "menu:reports"),
        (t(locale, "menu_profile"), "menu:profile"),
        (t(locale, "menu_delete_data"), "menu:delete"),
        (t(locale, "menu_restart_onboarding"), "menu:restart_onboarding"),
    ]
    if is_admin:
        buttons.append((t(locale, "menu_admin"), "menu:admin"))

    for text, callback in buttons:
        builder.button(text=text, callback_data=callback)
    builder.adjust(2)
    return builder.as_markup()


def reminders_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(locale, "reminder_meal"), callback_data="reminder:set:meal")
    builder.button(text=t(locale, "reminder_report"), callback_data="reminder:set:daily_report")
    builder.button(text=t(locale, "reminder_disable_meal"), callback_data="reminder:disable:meal")
    builder.button(text=t(locale, "reminder_disable_report"), callback_data="reminder:disable:daily_report")
    builder.adjust(2)
    return builder.as_markup()


def delete_keyboard(locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(locale, "delete_history"), callback_data="delete:history")
    builder.button(text=t(locale, "delete_profile_history"), callback_data="delete:profile_and_history")
    builder.button(text=t(locale, "delete_full_account"), callback_data="delete:full_account")
    builder.adjust(1)
    return builder.as_markup()


def delete_confirm_keyboard(locale: str, scope: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(locale, "delete_confirm"), callback_data=f"delete:confirm:{scope}"
                )
            ]
        ]
    )


def approval_keyboard(request_id: int, locale: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(locale, "approve"), callback_data=f"admin:approve:{request_id}")
    builder.button(text=t(locale, "reject"), callback_data=f"admin:reject:{request_id}")
    return builder.as_markup()


def admin_panel_keyboard(locale: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(locale, "admin_panel_link"), url=url)]
        ]
    )
