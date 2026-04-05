from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import (
    get_user, update_user_field, get_user_cars,
    get_user_active_bookings, add_car, delete_car_from_db
)
from app.utils.funcs import get_car_emoji
from app.utils.google_sheets import add_car_to_sheet, delete_car_from_sheet, update_user_in_sheet

import asyncio
import logging

router = Router()


class ProfileForm(StatesGroup):
    # Додавання авто
    adding_car_type = State()
    adding_car_number = State()
    # Редагування
    waiting_for_new_name = State()
    waiting_for_new_phone = State()
    deleting_car = State()



@router.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    tg_id = callback.from_user.id

    user = await get_user(tg_id)
    if not user:
        await callback.message.answer("Профіль не знайдено. Спочатку зареєструйтесь.")
        await callback.answer()
        return

    # Дістаємо машини та записи
    user_cars = await get_user_cars(tg_id)
    active_bookings = await get_user_active_bookings(tg_id)

    user_type_str = "Приватна особа" if user.type == "individual" else "Юридична особа"

    # Формуємо блок з машинами
    cars_text = ""
    if user_cars:
        for car in user_cars:
            c_emoji = get_car_emoji(car.type)
            c_type_ua = {"passenger": "Легковий", "off_roader": "Позашляховик", "van": "Мінівен"}.get(car.type,
                                                                                                      car.type)
            cars_text += f" {c_emoji} <code>{car.car_number}</code> ({c_type_ua})\n"
    else:
        cars_text = " Немає доданих авто\n"

    # Формуємо блок із записами
    bookings_text = ""
    if active_bookings:
        for b in active_bookings:
            b_date = b.date.strftime('%d.%m')
            b_time = b.time.strftime('%H:%M')
            bookings_text += f" 🗓 {b_date} о {b_time} | 🚗 {b.car_number} ({b.service})\n"
    else:
        bookings_text = " Немає активних записів\n"

    text = (
        f"👤 <b>ВАШ ПРОФІЛЬ</b>\n"
        f"───────────────\n"
        f"<b>Тип:</b> {user_type_str}\n"
        f"<b>Ім'я/Назва:</b> {user.name}\n"
        f"<b>Телефон:</b> {user.phone}\n\n"
        f"<b>ВАШ ГАРАЖ:</b>\n{cars_text}\n"
        f"📅 <b>АКТИВНІ ЗАПИСИ:</b>\n{bookings_text}"
        f"───────────────\n"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Додати авто", callback_data="prof_add_car")
    builder.button(text="⚙️ Змінити дані", callback_data="prof_edit_menu")
    builder.button(text="Назад", callback_data="controller_hub", style="primary")
    builder.adjust(2, 1)

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await callback.answer()



@router.callback_query(F.data == "prof_edit_menu")
async def edit_profile_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Змінити Ім'я", callback_data="edit_prof_name")
    builder.button(text="✏️ Змінити Телефон", callback_data="edit_prof_phone")
    builder.button(text="❌ Видалити авто", callback_data="prof_delete_car_menu")
    builder.button(text="Назад до профілю", callback_data="profile", style="primary")
    builder.adjust(2, 1, 1)

    await callback.message.edit_text("⚙️ <b>Що саме ви хочете змінити?</b>", reply_markup=builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.in_(["edit_prof_name", "edit_prof_phone"]))
async def start_edit_text_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_prof_", "")

    prompt = "Введіть нове ім'я / назву компанії:" if field == "name" else "Введіть новий номер телефону:"
    target_state = ProfileForm.waiting_for_new_name if field == "name" else ProfileForm.waiting_for_new_phone

    await state.set_state(target_state)

    builder = InlineKeyboardBuilder()
    builder.button(text="Скасувати", callback_data="prof_edit_menu", style="primary")

    new_msg = await callback.message.edit_text(prompt, reply_markup=builder.as_markup())
    await state.update_data(main_message_id=new_msg.message_id)
    await callback.answer()



@router.message(ProfileForm.waiting_for_new_name, F.text)
@router.message(ProfileForm.waiting_for_new_phone, F.text)
async def save_text_field(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    field_to_update = "name" if current_state == ProfileForm.waiting_for_new_name.state else "phone"

    await update_user_field(message.from_user.id, field_to_update, message.text)

    asyncio.create_task(update_user_in_sheet(
        tg_id=message.from_user.id,
        field=field_to_update,
        new_value=message.text
    ))

    data = await state.get_data()

    # Видаляємо повідомлення юзера та старе повідомлення бота
    try:
        await message.delete()
    except:
        pass
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=data.get("main_message_id"))
    except:
        pass

    builder = InlineKeyboardBuilder()
    builder.button(text="Повернутися в профіль", callback_data="profile")
    await message.answer("Дані успішно оновлено!", reply_markup=builder.as_markup(), style="success")
    await state.clear()



@router.callback_query(F.data == "prof_delete_car_menu")
async def delete_car_menu(callback: types.CallbackQuery, state: FSMContext):
    user_cars = await get_user_cars(callback.from_user.id)

    if not user_cars:
        await callback.answer("У вас немає авто для видалення.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for car in user_cars:
        builder.button(text=f"❌ {car.car_number}", callback_data=f"del_car_{car.car_number}")

    builder.button(text="Назад", callback_data="prof_edit_menu", style="primary")
    builder.adjust(1)

    await callback.message.edit_text("Оберіть авто, яке хочете видалити з гаража:", reply_markup=builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.startswith("del_car_"))
async def process_delete_car(callback: types.CallbackQuery):
    car_number = callback.data.replace("del_car_", "")
    await delete_car_from_db(car_number, callback.from_user.id)

    asyncio.create_task(delete_car_from_sheet(car_number=car_number))

    builder = InlineKeyboardBuilder()
    builder.button(text="Повернутися в профіль", callback_data="profile")
    await callback.message.edit_text(f"✅ Авто <code>{car_number}</code> видалено.", reply_markup=builder.as_markup())
    await callback.answer()



@router.callback_query(F.data == "prof_add_car")
async def start_add_car(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Легковий", callback_data="add_car_type_passenger")
    builder.button(text="🚙 Позашляховик", callback_data="add_car_type_offroader")
    builder.button(text="🚐 Мінівен / Бус", callback_data="add_car_type_van")
    builder.button(text="Скасувати", callback_data="profile", style="primary")
    builder.adjust(1)

    new_msg = await callback.message.edit_text("Оберіть тип вашого нового автомобіля:",
                                               reply_markup=builder.as_markup())

    await state.update_data(main_message_id=new_msg.message_id)
    await state.set_state(ProfileForm.adding_car_type)
    await callback.answer()


@router.callback_query(ProfileForm.adding_car_type, F.data.startswith("add_car_type_"))
async def process_add_car_type(callback: types.CallbackQuery, state: FSMContext):
    type_mapping = {
        "add_car_type_passenger": "passenger",
        "add_car_type_offroader": "off_roader",
        "add_car_type_van": "van"
    }
    car_type = type_mapping.get(callback.data)
    await state.update_data(car_type=car_type)

    await callback.message.edit_text("Введіть державний номер авто (наприклад, AA1234BB):")
    await state.set_state(ProfileForm.adding_car_number)
    await callback.answer()


@router.message(ProfileForm.adding_car_number, F.text)
async def process_add_car_number(message: types.Message, state: FSMContext):
    car_number = message.text.upper().strip()
    data = await state.get_data()

    # Видаляємо зайве з чату
    try:
        await message.delete()
    except:
        pass
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=data.get("main_message_id"))
    except:
        pass

    try:
        await add_car(tg_id=message.from_user.id, car_number=car_number, car_type=data['car_type'])

        asyncio.create_task(add_car_to_sheet(
            car_number=car_number, car_type=data['car_type'], tg_id=message.from_user.id
        ))

        text = f"✅ Авто <code>{car_number}</code> успішно додано до вашого гаража!"
    except Exception as e:
        logging.error(f"\033[31mПомилка додавання авто: {e}\033[0m")
        text = "❌ Помилка. Можливо, авто з таким номером вже існує в базі."

    builder = InlineKeyboardBuilder()
    builder.button(text="Повернутися в профіль", callback_data="profile", style="primary")

    await message.answer(text, reply_markup=builder.as_markup())
    await state.clear()