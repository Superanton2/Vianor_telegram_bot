import datetime
import os
from dotenv import load_dotenv

from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import get_worker_data, get_booked_times, get_booking_with_user_info

load_dotenv()
work_hours_str = os.getenv("WORK_HOURS")
WORK_HOURS = [hour.strip() for hour in work_hours_str.split(",")]
UKR_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

router = Router()


# 1. ПОКАЗУЄМО РОБОЧІ ДНІ ПРАЦІВНИКА
@router.callback_query(F.data == "worker_schedule")
async def show_worker_days(callback: types.CallbackQuery):
    worker = await get_worker_data(callback.from_user.id)

    if not worker or not worker.work_days:
        await callback.answer("У вас немає призначених робочих днів.", show_alert=True)
        return

    work_days = worker.work_days

    builder = InlineKeyboardBuilder()
    today = datetime.date.today()


    for i in range(5):
        target_date = today + datetime.timedelta(days=i)
        weekday = target_date.weekday()

        if weekday in work_days:
            day_name = UKR_DAYS[weekday]
            builder.button(
                text=f"{target_date.strftime('%d.%m')} {day_name}",
                callback_data=f"w_date_{target_date.isoformat()}"
            )

    builder.adjust(2)
    builder.button(text="Назад", callback_data="controller_hub", style="primary")

    await callback.message.edit_text(
        "📅 <b>Ваш розклад:</b>\nОберіть робочий день для перегляду:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("w_date_"))
async def show_worker_slots(callback: types.CallbackQuery):
    selected_date_str = callback.data.replace("w_date_", "")
    target_date = datetime.date.fromisoformat(selected_date_str)

    booked_times = await get_booked_times(target_date)

    builder = InlineKeyboardBuilder()

    for time_slot in WORK_HOURS:
        if time_slot in booked_times:
            builder.button(
                text=f"{time_slot}",
                callback_data=f"w_book_{selected_date_str}_{time_slot}",
                style="danger"
            )
        else:
            builder.button(
                text=f"{time_slot}",
                callback_data="w_free",
                style="success"
            )

    builder.adjust(3)
    builder.button(text="Розклад", callback_data="worker_schedule", style="primary")

    day_name = UKR_DAYS[target_date.weekday()]
    await callback.message.edit_text(
        f"⏰ <b>Розклад на {target_date.strftime('%d.%m')} ({day_name}):</b>\n\n"
        f"Червоне — зайнято (натисніть для деталей)\n"
        f"Зелене — вільно",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "w_free")
async def handle_free_slot(callback: types.CallbackQuery):
    await callback.answer("Цей час повністю вільний", show_alert=True)


@router.callback_query(F.data.startswith("w_book_"))
async def show_booking_details(callback: types.CallbackQuery):
    data_parts = callback.data.replace("w_book_", "").split("_")
    date_str = data_parts[0]
    time_str = data_parts[1]

    target_date = datetime.date.fromisoformat(date_str)
    target_time = datetime.datetime.strptime(time_str, '%H:%M').time()

    booking_info = await get_booking_with_user_info(target_date, target_time)

    if not booking_info:
        await callback.answer("Помилка: запис скасовано або не знайдено.", show_alert=True)
        return

    service, car_number, name, phone = booking_info

    text = (
        f"📋 <b>Деталі запису:</b>\n\n"
        f"🗓 Дата: {target_date.strftime('%d.%m.%Y')}\n"
        f"⏰ Час: {time_str}\n"
        f"───────────────\n"
        f"👤 Клієнт: {name}\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"🚗 Авто: <b>{car_number}</b>\n"
        f"🧽 Послуга: {service}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="День", callback_data=f"w_date_{date_str}", style="primary")

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()