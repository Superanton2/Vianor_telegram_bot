from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.db.db_requests import add_user, add_car
from app.utils.funcs import get_car_emoji
import logging

router = Router()

class RegisterForm(StatesGroup):
    choosing_type = State()
    entering_name = State()
    entering_phone = State()
    entering_car_type = State()
    entering_car_number = State()


@router.callback_query(F.data == "registration")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Приватна особа", callback_data="type_individual")
    builder.button(text="🏢 Юридична особа", callback_data="type_business")
    builder.adjust(1)

    await callback.message.answer(
        "[1/5] Давайте зареєструємось!\nОберіть ваш тип:",
        reply_markup=builder.as_markup()
    )

    await state.set_state(RegisterForm.choosing_type)
    await callback.answer()


@router.callback_query(RegisterForm.choosing_type, F.data.in_(["type_individual", "type_business"]))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "type_individual":
        user_type = "individual"
    else:
        user_type = "business"
    await state.update_data(user_type=user_type)

    if user_type == "individual":
        text = "[2/5] Введіть ваше ім'я та прізвище:"
    else:
        text = "[2/5] Введіть назву вашої компанії:"

    await state.update_data(main_message_id=callback.message.message_id)

    await callback.message.edit_text(text)

    await state.set_state(RegisterForm.entering_name)
    await callback.answer()


@router.message(RegisterForm.entering_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    data = await state.get_data()
    main_msg_id = data.get("main_message_id")

    # delete message from user
    try:
        await message.delete()
    except Exception:
        pass

    # delete old main massage
    if main_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=main_msg_id)
        except Exception:
            pass


    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Надіслати мій номер", request_contact=True)

    new_msg = await message.answer(
        "[3/5] Введіть ваш номер телефону або натисніть кнопку нижче:",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.update_data(main_message_id=new_msg.message_id)
    await state.set_state(RegisterForm.entering_phone)


@router.message(RegisterForm.entering_phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_msg_id = data.get("main_message_id")

    # delete message from user
    try:
        await message.delete()
    except Exception:
        pass

    # delete old main massage
    if main_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=main_msg_id)
        except Exception:
            pass

    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text
    else:
        await message.answer("[3/5] Будь ласка, надішліть номер телефону текстом або контактом.")
        return

    await state.update_data(phone=phone)

    try:
        await message.delete_reply_markup()
    except Exception:
        pass

    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Легковий", callback_data="car_type_passenger")
    builder.button(text="🚙 Позашляховик", callback_data="car_type_offroader")
    builder.button(text="🚐 Мінівен / Бус", callback_data="car_type_van")
    builder.adjust(1)


    await message.answer(
        "[4/5] Оберіть тип вашого автомобіля:",
        reply_markup=builder.as_markup()
    )

    await state.set_state(RegisterForm.entering_car_type)



@router.callback_query(RegisterForm.entering_car_type, F.data.startswith("car_type_"))
async def process_car_type(callback: types.CallbackQuery, state: FSMContext):
    type_mapping = {
        "car_type_passenger": "passenger",
        "car_type_offroader": "off_roader",
        "car_type_van": "van"
    }
    car_type = type_mapping.get(callback.data)
    await state.update_data(car_type=car_type)

    new_msg = await callback.message.edit_text(
        "[5/5] Введіть державний номер вашого авто (наприклад, AA1234BB):"
    )
    await state.update_data(main_message_id=new_msg.message_id)

    await state.set_state(RegisterForm.entering_car_number)
    await callback.answer()

@router.message(RegisterForm.entering_car_number, F.text)
async def process_car_number(message: types.Message, state: FSMContext):
    car_number = message.text.upper().strip() # Одразу робимо великими літерами і прибираємо пробіли

    data = await state.get_data()
    user_type = data['user_type']
    name = data['name']
    phone = data['phone']
    car_type = data['car_type']
    main_msg_id = data.get("main_message_id")

    # Одразу видаляємо повідомлення юзера з номером
    try:
        await message.delete()
    except Exception:
        pass

    from app.db.db_requests import get_car_by_number
    existing_car = await get_car_by_number(car_number)

    if existing_car:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            text=f"❌ Авто з номером <b>{car_number}</b> вже зареєстровано!\n\n"
                 f"[5/5] Введіть інший державний номер вашого авто:"
        )
        return

    try:
        await add_user(
            tg_id=message.from_user.id,
            user_type=user_type,
            name=name,
            phone=phone
        )

        await add_car(
            tg_id=message.from_user.id,
            car_number=car_number,
            car_type=car_type
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="Продовжити", callback_data="controller_hub")

        car_emoji = get_car_emoji(data['car_type'])
        display_type = {
            "passenger": "Легковий",
            "off_roader": "Позашляховик",
            "van": "Мінівен / Бус"
        }.get(car_type, car_type)

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            text=f"🎉 <b>Реєстрація успішна!</b>\n\n"
            f"👤 Ваші дані: {name}\n"
            f"📱 Телефон: {phone}\n"
            f"{car_emoji} Авто: {car_number} ({display_type})\n\n"
            f"Тепер ви можете записатися на мийку.",
            reply_markup=builder.as_markup()
        )
        await state.clear()

    except Exception as e:
        builder = InlineKeyboardBuilder()
        builder.button(text="Спробувати ще раз", callback_data="registration")
        logging.error(f"\033[31mПомилка БД під час реєстрації: {e}\033[0m")

        await message.answer(
            text="Виникла помилка під час збереження. Спробуйте ще раз.",
            reply_markup=builder.as_markup()
        )
        await state.clear()

@router.message(RegisterForm.entering_car_number, F.text)
async def process_car_number(message: types.Message, state: FSMContext):
    car_number = message.text.upper().strip()

    data = await state.get_data()
    user_type = data['user_type']
    name = data['name']
    phone = data['phone']
    car_type = data['car_type']
    main_msg_id = data.get("main_message_id")

    try:
        await message.delete()
    except Exception:
        pass


    from app.db.db_requests import get_car_by_number
    existing_car = await get_car_by_number(car_number)

    if existing_car:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            text=f"❌ Авто з номером <b>{car_number}</b> вже зареєстровано!\n\n"
                 f"[5/5] Введіть інший державний номер вашого авто:"
        )
        return

    try:
        await add_user(
            tg_id=message.from_user.id,
            user_type=user_type,
            name=name,
            phone=phone
        )

        await add_car(
            tg_id=message.from_user.id,
            car_number=car_number,
            car_type=car_type
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="Продовжити", callback_data="controller_hub", style="success")

        car_emoji = get_car_emoji(data['car_type'])

        display_type = {
            "passenger": "Легковий",
            "off_roader": "Позашляховик",
            "van": "Мінівен / Бус"
        }.get(car_type, car_type)


        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=main_msg_id,
            text=f"🎉 <b>Реєстрація успішна!</b>\n\n"
                 f"👤 Ваші дані: {name}\n"
                 f"📱 Телефон: {phone}\n"
                 f"{car_emoji} Авто: {car_number} ({display_type})\n\n"
                 f"Тепер ви можете записатися на мийку.",
            reply_markup=builder.as_markup()
        )
        await state.clear()
    except Exception as e:
        builder = InlineKeyboardBuilder()
        builder.button(text="Спробувати ще раз", callback_data="registration")
        logging.error(f"\033[31mПомилка БД під час реєстрації: {e}\033[0m")

        await message.answer(
            text="Виникла помилка під час збереження. Спробуйте ще раз.",
            reply_markup=builder.as_markup()
        )
        await state.clear()