import datetime
import os
from dotenv import load_dotenv

from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import get_user_active_bookings, get_booking_by_id, cancel_booking, get_car_by_number
from app.utils.funcs import get_car_emoji, get_service_emoji
from app.utils.price import get_price

load_dotenv()
CANCEL_TIME_LIMIT = int(os.getenv("CANCEL_TIME_LIMIT", "2"))

router = Router()


@router.callback_query(F.data == "my_bookings_menu")
async def show_my_bookings(callback: types.CallbackQuery):
    active_bookings = await get_user_active_bookings(callback.from_user.id)

    if not active_bookings:
        await callback.answer("У вас немає активних записів.", show_alert=True)
        return

    text = "📅 <b>Ваші активні записи:</b>\n\n"
    builder = InlineKeyboardBuilder()

    # Генеруємо блок тексту для кожного запису
    for b in active_bookings:
        car = await get_car_by_number(b.car_number)
        car_type = car.type if car else "passenger"
        price = await get_price(car_type, b.service)

        b_date = b.date.strftime('%d.%m.%Y')
        b_time = b.time.strftime('%H:%M')

        car_emoji = get_car_emoji(car_type)
        service_emoji = get_service_emoji(b.service)

        text += (
            f"{car_emoji} Авто: {b.car_number}\n"
            f"📅 Дата: {b_date}\n"
            f"⏰ Час: {b_time}\n"
            f"{service_emoji} Послуга: {b.service}\n"
            f"💵 Ціна: {price} грн\n"
            f"───────────────\n"
        )

        # Створюємо кнопку для зміни саме цього запису
        builder.button(text=f"Змінити запис {b.car_number}", callback_data=f"edit_book_{b.id}")

    builder.button(text="Назад", callback_data="controller_hub", style="primary")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("edit_book_"))
async def edit_booking(callback: types.CallbackQuery):
    booking_id = int(callback.data.replace("edit_book_", ""))
    booking = await get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("Запис не знайдено.", show_alert=True)
        return


    booking_dt = datetime.datetime.combine(booking.date, booking.time)
    now = datetime.datetime.now()
    time_diff = booking_dt - now

    if time_diff.total_seconds() < CANCEL_TIME_LIMIT * 3600:
        await callback.answer(
            f"На жаль, скасувати чи змінити запис можна не пізніше ніж за {CANCEL_TIME_LIMIT} год. до мийки. Зателефонуйте адміністратору.",
            show_alert=True
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Скасувати запис", callback_data=f"delete_book_{booking.id}", style="danger")
    builder.button(text="Назад", callback_data="my_bookings_menu", style="primary")
    builder.adjust(1)

    await callback.message.edit_text(
        f"Ви бажаєте скасувати запис для авто {booking.car_number} на {booking.date.strftime('%d.%m')} о {booking.time.strftime('%H:%M')}?\n\n"
        f"Після скасування ви зможете обрати новий час.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_book_"))
async def delete_booking_handler(callback: types.CallbackQuery):
    booking_id = int(callback.data.replace("delete_book_", ""))

    await cancel_booking(booking_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="Записатись наново", callback_data="booking")
    builder.button(text="В головне меню", callback_data="controller_hub", style="primary")
    builder.adjust(1)

    await callback.message.edit_text(
        "Ваш запис успішно скасовано.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()