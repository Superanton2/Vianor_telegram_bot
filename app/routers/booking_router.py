import datetime
import os
from dotenv import load_dotenv

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import (add_booking, get_booked_times, check_if_day_full, get_user_cars,
                                get_car_by_number, get_active_booking_for_car)
from app.utils.keyboards import create_cars_keyboard
from app.utils.price import get_price
from app.utils.funcs import get_car_emoji, get_service_emoji

load_dotenv()
work_hours_str = os.getenv("WORK_HOURS")
WORK_HOURS = [hour.strip() for hour in work_hours_str.split(",")]
TOTAL_SLOTS = len(WORK_HOURS)
UKR_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
HOURS_BEFORE_BOOKING = float(os.getenv("HOURS_BEFORE_BOOKING", "1"))

router = Router()


class BookingForm(StatesGroup):
    choosing_car = State()
    choosing_day = State()
    choosing_time = State()
    choosing_service = State()
    confirming = State()


async def update_screen(message: types.Message, state: FSMContext, text: str, markup):
    await state.update_data(last_text=text, last_markup=markup)
    await message.edit_text(text, reply_markup=markup)



@router.callback_query(F.data.in_(["booking", "booking_new"]))
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    user_cars = await get_user_cars(callback.from_user.id)

    if not user_cars:
        await callback.answer(
            text="У вас немає зареєстрованих авто! Спочатку додайте авто в профілі.",
            show_alert=True
        )
        return

    # one car
    if len(user_cars) == 1:
        car_number = user_cars[0].car_number

        existing_booking = await get_active_booking_for_car(car_number)
        if existing_booking:
            b_date = existing_booking.date.strftime('%d.%m')
            b_time = existing_booking.time.strftime('%H:%M')
            await callback.answer(
                f"❌ Ваше авто вже записане на {b_date} о {b_time}.\n"
                f"Скасуйте попередній запис у профілі, щоб створити новий.",
                show_alert=True
            )
            return

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await state.update_data(car_number=car_number)

        builder = InlineKeyboardBuilder()
        today = datetime.date.today()

        for i in range(7):
            target_date = today + datetime.timedelta(days=i)
            day_name = UKR_DAYS[target_date.weekday()]
            is_fully_booked = await check_if_day_full(target_date, TOTAL_SLOTS)

            if is_fully_booked:
                builder.button(
                    text=f"{target_date.strftime('%d.%m')} {day_name}",
                    callback_data="booked_day"
                )
            else:
                builder.button(
                    text=f"{target_date.strftime('%d.%m')} {day_name}",
                    callback_data=f"book_date_{target_date.isoformat()}",
                    style="success"
                )

        builder.adjust(2)
        builder.button(
            text="Назад",
            callback_data="controller_hub",
            style="danger"
        )

        await state.set_state(BookingForm.choosing_day)
        text = f"[2/5] 📅 Оберіть день для запису авто {car_number}:"
        markup = builder.as_markup()

        try:
            await callback.message.edit_text(text, reply_markup=markup)
            await state.update_data(main_message_id=callback.message.message_id)
        except Exception:
            sent_msg = await callback.message.answer(text, reply_markup=markup)
            await state.update_data(main_message_id=sent_msg.message_id)

        await state.update_data(last_text=text, last_markup=markup)
        await callback.answer()
        return

    # couple cars
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    text = "[1/5] Оберіть авто для запису:"
    markup = create_cars_keyboard(user_cars).as_markup()

    await state.set_state(BookingForm.choosing_car)

    try:
        await callback.message.edit_text(text, reply_markup=markup)
        await state.update_data(main_message_id=callback.message.message_id)
    except Exception:
        sent_msg = await callback.message.answer(text, reply_markup=markup)
        await state.update_data(main_message_id=sent_msg.message_id)

    await state.update_data(last_text=text, last_markup=markup)
    await callback.answer()



@router.callback_query(F.data.startswith("book_car_"))
async def process_car(callback: types.CallbackQuery, state: FSMContext):
    car_number = callback.data.replace("book_car_", "")

    existing_booking = await get_active_booking_for_car(car_number)
    if existing_booking:
        b_date = existing_booking.date.strftime('%d.%m')
        b_time = existing_booking.time.strftime('%H:%M')

        await callback.answer(
            f"❌ Це авто вже записане на {b_date} о {b_time}.\n"
            f"Скасуйте попередній запис у профілі, щоб створити новий.",
            show_alert=True
        )
        return

    await state.update_data(car_number=car_number)

    builder = InlineKeyboardBuilder()
    today = datetime.date.today()

    for i in range(7):
        target_date = today + datetime.timedelta(days=i)
        day_name = UKR_DAYS[target_date.weekday()]

        is_fully_booked = await check_if_day_full(target_date, TOTAL_SLOTS)

        if is_fully_booked:
            builder.button(
                text=f"{target_date.strftime('%d.%m')} {day_name}",
                callback_data="booked_day",
                # style="danger"
            )
        else:
            builder.button(
                text=f"{target_date.strftime('%d.%m')} {day_name}",
                callback_data=f"book_date_{target_date.isoformat()}",
                style="success",
            )

    builder.adjust(2)
    user_cars = await get_user_cars(callback.from_user.id)
    if len(user_cars) == 1:
        builder.button(
            text="Назад",
            callback_data="controller_hub",
            style="danger"
        )
    else:
        builder.button(
            text="Назад",
            callback_data="booking",
            style="danger"
        )

    await state.set_state(BookingForm.choosing_day)
    await update_screen(callback.message, state, f"[2/5] 📅 Оберіть день для запису авто {car_number}:",
                        builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.startswith("book_date_"))
async def process_day(callback: types.CallbackQuery, state: FSMContext):
    selected_date_str = callback.data.replace("book_date_", "")
    await state.update_data(date=selected_date_str)

    target_date = datetime.date.fromisoformat(selected_date_str)
    booked_times = await get_booked_times(target_date)

    builder = InlineKeyboardBuilder()

    now = datetime.datetime.now()
    for time_slot in WORK_HOURS:

        slot_time = datetime.datetime.strptime(time_slot, '%H:%M').time()
        slot_datetime = datetime.datetime.combine(target_date, slot_time)
        time_diff = slot_datetime - now

        if time_slot in booked_times or time_diff.total_seconds() < HOURS_BEFORE_BOOKING * 3600:
            builder.button(
                text=time_slot,
                callback_data="booked_time",
                # style="danger"
            )
        else:
            builder.button(
                text=time_slot,
                callback_data=f"book_time_{time_slot}",
                style="success"
            )
    data = await state.get_data()
    car_number = data.get('car_number')
    builder.button(text="Назад", callback_data=f"book_car_{car_number}", style="danger")
    builder.adjust(3)

    await state.set_state(BookingForm.choosing_time)
    await update_screen(callback.message, state, f"[3/5] ⏰ Оберіть вільний час на {selected_date_str}:",
                        builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.startswith("book_time_"))
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.replace("book_time_", "")
    await state.update_data(time=selected_time)

    builder = InlineKeyboardBuilder()
    builder.button(text="💦 Безконтактна мийка", callback_data="srv_Безконтактна мийка")
    builder.button(text="🧹 Мийка, Пилосос", callback_data="srv_Мийка, Пилосос")
    builder.button(text="✨ Комплекс", callback_data="srv_Комплекс")

    data = await state.get_data()
    b_date = data.get('date')
    builder.button(text="Назад", callback_data=f"book_date_{b_date}", style="danger")
    builder.adjust(1)

    await state.set_state(BookingForm.choosing_service)
    await update_screen(callback.message, state, "[4/5] 🧽 Оберіть послугу:", builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.startswith("srv_"))
async def process_service(callback: types.CallbackQuery, state: FSMContext):
    service = callback.data.replace("srv_", "")
    await state.update_data(service=service)
    data = await state.get_data()

    car = await get_car_by_number(data['car_number'])
    car_type = car.type if car else "passenger"

    price = await get_price(car_type, data['service'])
    car_emoji = get_car_emoji(car_type)
    service_emoji = get_service_emoji(data['service'])

    core_text = (
        f"{car_emoji} Авто: {data['car_number']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Час: {data['time']}\n"
        f"{service_emoji} Послуга: {data['service']}\n"
        f"💵 Ціна: {price}"
    )
    await state.update_data(core_text=core_text)

    text = f"[5/5] 📋 <b>Перевірте деталі запису:</b>\n\n{core_text}\n\nПідтверджуєте запис?"
    builder = InlineKeyboardBuilder()
    builder.button(text="Підтвердити", callback_data="confirm_booking", style="success")
    builder.button(text="Скасувати", callback_data="confirm_cancel_booking", style="danger")

    await state.set_state(BookingForm.confirming)
    await update_screen(callback.message, state, text, builder.as_markup())
    await callback.answer()



@router.callback_query(F.data == "confirm_booking")
async def save_booking_final(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    try:
        b_date = datetime.date.fromisoformat(data['date'])
        b_time = datetime.datetime.strptime(data['time'], '%H:%M').time()

        await add_booking(
            tg_id=callback.from_user.id,
            b_date=b_date,
            b_time=b_time,
            service=data['service'],
            car_number=data['car_number']
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="В головне меню", callback_data="controller_hub")

        success_text = (f"🎉 <b>Ваш запис успішно створено!</b>\n\n"
                        f"{data['core_text']}\n\n"
                        f"Чекаємо на вас у визначений час!")
        await callback.message.edit_text(
            text= success_text,
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        import logging
        logging.error(f"\033[31mПомилка запису в БД: {e}\033[0m")
        await callback.message.edit_text("Виникла помилка при записі. Спробуйте ще раз пізніше.")

    await state.clear()
    await callback.answer()




@router.callback_query(F.data == "confirm_cancel_booking")
async def confirm_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="В головне меню", callback_data="controller_hub", style="primary")

    await callback.message.edit_text("‼️Запис скасовано.", reply_markup=builder.as_markup())
    await callback.answer()



@router.callback_query(F.data == "resume_booking")
async def resume_booking(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    last_text = data.get("last_text")
    last_markup = data.get("last_markup")

    if last_text and last_markup:
        await callback.message.edit_text(last_text, reply_markup=last_markup)
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="В головне меню", callback_data="controller_hub")
        await callback.message.edit_text("Сталася помилка відновлення. Почніть спочатку.",
                                         reply_markup=builder.as_markup())
        await state.clear()

    await callback.answer()



@router.callback_query(F.data.in_(["booked_day", "booked_time"]))
async def handle_booked_slot(callback: types.CallbackQuery):
    await callback.answer("Цей слот вже повністю зайнятий ❌ Оберіть інший.", show_alert=True)