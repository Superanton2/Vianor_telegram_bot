from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.callback_query(F.data == "registration")
async def registration(callback: types.CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    builder = InlineKeyboardBuilder()

    builder.button(text="Назад", callback_data="controller_hub", style = "primary")

    await callback.message.answer("Це реєстрація", reply_markup=builder.as_markup())
    await callback.answer()

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.db.db_requests import add_user
from app.utils.keyboards import create_main_user_keyboard

router = Router()

class RegisterForm(StatesGroup):
    choosing_type = State()
    entering_name = State()
    entering_phone = State()
    entering_car = State()



@router.callback_query(F.data == "registration")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Приватна особа", callback_data="type_individual")
    builder.button(text="🏢 Юридична особа", callback_data="type_business")
    builder.adjust(2)

    await callback.message.answer(
        "Давайте зареєструємось!\nОберіть ваш тип:",
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
        text = "Введіть ваше ім'я та прізвище:"
    else:
        text = "Введіть назву вашої компанії:"

    await callback.message.answer(text)

    await state.set_state(RegisterForm.entering_name)
    await callback.answer()


@router.message(RegisterForm.entering_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Надіслати мій номер", request_contact=True)

    await message.answer(
        "Введіть ваш номер телефону (або натисніть кнопку нижче, щоб поділитися контактом):",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(RegisterForm.entering_phone)


@router.message(RegisterForm.entering_phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text
    else:
        await message.answer("Будь ласка, надішліть номер телефону текстом або контактом.")
        return

    await state.update_data(phone=phone)

    await message.answer(
        "Супер! Останній крок: введіть державний номер вашого авто (наприклад, AA1234BB):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(RegisterForm.entering_car)


@router.message(RegisterForm.entering_car, F.text)
async def process_car(message: types.Message, state: FSMContext):
    car_number = message.text

    data = await state.get_data()
    user_type = data['user_type']
    name = data['name']
    phone = data['phone']

    try:
        await add_user(
            tg_id=message.from_user.id,
            user_type=user_type,
            car_num=car_number,
            name=name,
            phone=phone
        )

        builder = InlineKeyboardBuilder()

        builder.button(text="Продовжити", callback_data="controller_hub", style="primary")

        await message.answer(
            f"🎉 <b>Реєстрація успішна!</b>\n\n"
            f"👤 Ваші дані: {name}\n"
            f"📱 Телефон: {phone}\n"
            f"🚗 Авто: {car_number}\n\n"
            f"Тепер ви можете записатися на мийку.",
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        print(f"Помилка реєстрації БД: {e}")
        await message.answer("Виникла помилка при збереженні. Можливо, ви вже зареєстровані.")

    await state.clear()