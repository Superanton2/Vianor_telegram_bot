from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.funcs import log_to_sheets
import app.db.db_requests as db

import os
from dotenv import load_dotenv

load_dotenv()
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS").split(",")]

router = Router()

@router.callback_query(F.data == "permission_control")
async def permission_control_menu(callback: types.CallbackQuery):
    await show_delete_menu(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


async def show_delete_menu(message: types.Message, user_id: int, edit: bool = False):
    is_super_admin = user_id in SUPER_ADMINS

    workers = await db.get_all_workers()
    admins = await db.get_all_admins()

    builder = InlineKeyboardBuilder()

    if workers:
        for worker in workers:
            builder.button(
                text=f"Працівник: {worker.name}",
                callback_data=f"ask_deact_worker_{worker.telegram_id}",
                style="danger"
            )

    if is_super_admin and admins:
        for admin in admins:
            if admin.telegram_id not in SUPER_ADMINS:
                builder.button(
                    text=f"🔑 Адмін: {admin.name}",
                    callback_data=f"ask_deact_admin_{admin.telegram_id}",
                    style="danger"
                )

    builder.button(text="Назад", callback_data="admin_staff_manage", style="primary")
    builder.adjust(1)

    text = "🛡 <b>Керування доступом</b>\nОберіть людину, яку хочете деактивувати:"

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "delete_person")
async def delete_person_menu(callback: types.CallbackQuery):
    await show_delete_menu(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("ask_deact_"))
async def ask_deactivate_person(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    role = data_parts[2]  # "worker" or "admin"
    target_id = int(data_parts[3])

    target_name = "Невідомо"
    if role == "worker":
        workers = await db.get_all_workers()
        target_name = next((w.name for w in workers if w.telegram_id == target_id), str(target_id))
        role_ua = "працівника"
    else:
        admins = await db.get_all_admins()
        target_name = next((a.name for a in admins if a.telegram_id == target_id), str(target_id))
        role_ua = "адміністратора"

    text = f"⚠️ Ви впевнені, що хочете деактивувати {role_ua} <b>{target_name}</b> (<code>{target_id}</code>)?"

    builder = InlineKeyboardBuilder()
    builder.button(text="Так, деактивувати", callback_data=f"confirm_deact_{role}_{target_id}", style="danger")
    builder.button(text="Скасувати", callback_data="permission_control", style="primary")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_deact_"))
async def confirm_deactivate_person(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    role = data_parts[2]
    target_id = int(data_parts[3])

    target_name = "Невідомо"

    if role == "worker":
        workers = await db.get_all_workers()
        target_name = next((w.name for w in workers if w.telegram_id == target_id), str(target_id))
        await db.remove_worker(target_id)
        role_ua = "працівника"
    else:
        admins = await db.get_all_admins()
        target_name = next((a.name for a in admins if a.telegram_id == target_id), str(target_id))
        await db.remove_admin(target_id)
        role_ua = "адміністратора"

    await callback.message.edit_text(
        f"⚠️ Ви успішно деактивували {role_ua} <a href='tg://user?id={target_id}'>{target_name}</a>.",
        parse_mode="HTML",
        reply_markup=None
    )

    adder_name = callback.from_user.full_name
    for super_admin in SUPER_ADMINS:
        try:
            await callback.bot.send_message(
                chat_id=int(super_admin),
                text=f"ℹ️ <b>Лог безпеки</b>\n{adder_name} деактивував {role_ua}: "
                     f"<a href='tg://user?id={target_id}'>{target_name}</a>.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    log_text = f"Користувач {adder_name} деактивував {role_ua} {target_name} (ID: {target_id})"
    await log_to_sheets(log_text)
    await show_delete_menu(callback.message, callback.from_user.id, edit=False)
    await callback.answer()