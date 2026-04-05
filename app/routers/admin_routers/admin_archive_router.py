from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from sqlalchemy import select, func
import os


from app.db.db_setup import engine, admin_list, worker_list, bookings
from app.utils.google_sheets import sync_prices_to_db

router = Router()
SHEET_URL = os.getenv("SHEET_URL")


async def get_admin_stats():
    """Збирає статистику для дешборду в боті"""
    async with engine.begin() as conn:

        admins_q = await conn.execute(
            select(func.count()).select_from(admin_list).where(admin_list.c.is_active == True))
        admins_count = admins_q.scalar()


        workers_q = await conn.execute(
            select(func.count()).select_from(worker_list).where(worker_list.c.is_active == True))
        workers_count = workers_q.scalar()


        thirty_days_ago = datetime.now() - timedelta(days=30)
        income_q = await conn.execute(
            select(func.sum(bookings.c.price))
            .where(bookings.c.date >= thirty_days_ago)
            .where(bookings.c.status == "Виконано")
        )
        total_income = income_q.scalar() or 0

    return admins_count, workers_count, total_income


@router.callback_query(F.data == "admin_archive")
async def admin_archive(callback: types.CallbackQuery):

    admins_count, workers_count, total_income = await get_admin_stats()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Відкрити таблицю", url=SHEET_URL)
    keyboard.button(text="🔄 Оновити ціни зараз", callback_data="sync_prices_now")
    keyboard.button(text="Назад", callback_data="controller_hub", style="primary")
    keyboard.adjust(1)

    text = (
        f"<b>Google таблиця</b>\n\n"
        f"🔑 Адмінів: <code>{admins_count}</code>\n"
        f"👥 Працівників: <code>{workers_count}</code>\n"
        f"💰 Дохід (30 днів): <code>{total_income} грн</code>\n\n"
        f"<i>Ви можете оновити прайс-лист з Google Таблиці вручну:</i>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sync_prices_now")
async def handle_sync_prices(callback: types.CallbackQuery):
    await callback.answer("⏳ Оновлення цін...")

    try:
        new_prices = await sync_prices_to_db()
        await callback.message.answer(f"✅ Ціни успішно оновлено! Отримано послуг: {len(new_prices)}")
    except Exception as e:
        await callback.message.answer(f"❌ Помилка при оновленні: {e}")