import datetime
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import add_booking, get_booked_times, check_if_day_full

import os
from dotenv import load_dotenv

load_dotenv()
work_hours_str = os.getenv("WORK_HOURS")
WORK_HOURS = [hour.strip() for hour in work_hours_str.split(",")]
UKR_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

router = Router()

from aiogram.fsm.state import StatesGroup, State

class BookingForm(StatesGroup):
    choosing_car = State()
    choosing_day = State()
    choosing_time = State()
    choosing_service = State()
    choosing_category = State()
    confirming = State()


@router.callback_query(F.data == "booking")
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    today = datetime.date.today()

    for i in range(7):
        target_date = today + datetime.timedelta(days=i)
        day_name = UKR_DAYS[target_date.weekday()]

        is_fully_booked = await check_if_day_full(target_date, len(WORK_HOURS))
        # is_fully_booked = False  # Заглушка

        if is_fully_booked:
            builder.button(
                text=f"{target_date.strftime('%d.%m')} {day_name}",
                callback_data="booked_day",
                style="danger"
            )
        else:
            builder.button(
                text=f"{target_date.strftime('%d.%m')} {day_name}",
                callback_data=f"book_date_{target_date.isoformat()}",
                style="success",
            )

    builder.adjust(2)
    builder.button(text="Назад", callback_data="controller_hub", style="primary")

    await state.set_state(BookingForm.choosing_day)
    await callback.message.edit_text("📅 Оберіть день для запису:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.in_(["booked_day", "booked_time"]))
async def handle_booked_slot(callback: types.CallbackQuery):
    await callback.answer("Цей слот вже повністю зайнятий ❌ Оберіть інший.", show_alert=True)


@router.callback_query(BookingForm.choosing_day, F.data.startswith("book_date_"))
async def process_day(callback: types.CallbackQuery, state: FSMContext):
    selected_date = callback.data.replace("book_date_", "")
    await state.update_data(date=selected_date)

    builder = InlineKeyboardBuilder()

    booked_times = await get_booked_times(selected_date)
    # booked_times = ["10:00", "14:00"]  # Заглушка: ці години вже зайняті

    for time_slot in WORK_HOURS:
        if time_slot in booked_times:
            builder.button(
                text=time_slot,
                callback_data="booked_time",
                style="danger"
            )
        else:
            builder.button(
                text=time_slot,
                callback_data=f"book_time_{time_slot}",
                style="success"
            )

    builder.adjust(3)
    builder.button(text="Назад", callback_data="booking", style="primary")

    await state.set_state(BookingForm.choosing_time)
    await callback.message.edit_text(f"⏰ Оберіть час на {selected_date}:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(BookingForm.choosing_time, F.data.startswith("book_time_"))
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.replace("book_time_", "")
    await state.update_data(time=selected_time)

    builder = InlineKeyboardBuilder()
    builder.button(text="Безконтактна мийка", callback_data="service_wash")
    builder.button(text="Пилосос", callback_data="service_vacuum")
    builder.button(text="Комплекс", callback_data="service_complex")
    builder.adjust(1)

    await state.set_state(BookingForm.choosing_service)
    await callback.message.edit_text("🧽 Оберіть послугу:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(BookingForm.choosing_service, F.data.startswith("service_"))
async def process_service(callback: types.CallbackQuery, state: FSMContext):
    service = callback.data.replace("service_", "")

    if service == "wash":
        builder = InlineKeyboardBuilder()
        builder.button(text="🚗 Легковий", callback_data="cat_passenger")
        builder.button(text="🚙 Позашляховик", callback_data="cat_off_roader")
        builder.button(text="🚐 Мінівен / Бус", callback_data="cat_van")
        builder.adjust(1)

        await state.set_state(BookingForm.choosing_category)
        await callback.message.edit_text("Оберіть категорію вашого авто:", reply_markup=builder.as_markup())
    else:
        if service == "vacuum":
            service_name = "Пилосос"
        else:
            service_name = "Комплекс"
        await state.update_data(final_service=service_name)
        await show_confirmation(callback.message, state)

    await callback.answer()


@router.callback_query(BookingForm.choosing_category, F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    await state.update_data(final_service=f"Безконтактна мийка ({category})")

    await show_confirmation(callback.message, state)
    await callback.answer()


async def show_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()

    text = (
        f"📋 <b>Перевірте деталі запису:</b>\n\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Час: {data['time']}\n"
        f"🧽 Послуга: {data['final_service']}\n\n"
        f"Підтверджуєте запис?"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Підтвердити", callback_data="confirm_booking")
    builder.button(text="❌ Скасувати", callback_data="cancel_booking")
    # builder.button(text="❌ Скасувати", callback_data="controller_hub")

    await state.set_state(BookingForm.confirming)
    await message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(BookingForm.confirming, F.data == "confirm_booking")
async def save_booking(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = callback.from_user.id

    try:
        b_date = datetime.date.fromisoformat(data['date'])
        b_time = datetime.datetime.strptime(data['time'], '%H:%M').time()

        await add_booking(tg_id, b_date, b_time, data['final_service'])

        await callback.message.edit_text(
            "🎉 <b>Ваш запис успішно створено!</b>\nЧекаємо на вас у визначений час.",
            reply_markup=None
        )
    except Exception as e:
        print(f"Помилка запису: {e}")
        await callback.message.edit_text("Виникла помилка. Спробуйте ще раз пізніше.")

    await state.clear()
    await callback.answer()


@router.callback_query(BookingForm.confirming, F.data == "cancel_booking")
async def cancel_booking_flow(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запис скасовано. Повертаємось у головне меню.")
    await callback.answer()