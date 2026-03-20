from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.db_requests import get_user, update_user_field

router = Router()

class EditProfile(StatesGroup):
    waiting_for_new_value = State()


@router.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Профіль не знайдено. Спочатку зареєструйтесь.")
        await callback.answer()
        return

    if user.type == "individual":
        user_type_str= "Приватна особа"
    else:
        user_type_str= "Юридична особа"

    text = (
        f"👤 <b>ВАШ ПРОФІЛЬ</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"<b>Тип:</b> {user_type_str}\n"
        f"<b>Ім'я/Назва:</b> {user.name}\n"
        f"<b>Телефон:</b> {user.phone}\n"
        f"<b>Авто:</b> {user.car_number}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"<i>Якщо знайшли помилку, оберіть поле для редагування:</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Ім'я", callback_data="edit_prof_name")
    builder.button(text="✏️ Телефон", callback_data="edit_prof_phone")
    builder.button(text="✏️ Авто", callback_data="edit_prof_car_number")
    builder.button(text="🔙 Назад", callback_data="controller_hub")
    builder.adjust(3, 1)  # Three buttons in a row, the Back button below

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await callback.answer()


@router.callback_query(F.data.startswith("edit_prof_"))
async def start_edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_prof_", "")

    prompts = {
        "name": "Введіть нове ім'я / назву компанії:",
        "phone": "Введіть новий номер телефону:",
        "car_number": "Введіть новий номер авто:"
    }

    await state.update_data(editing_field=field)
    await state.set_state(EditProfile.waiting_for_new_value)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Скасувати", callback_data="profile", style="danger")

    await callback.message.edit_text(
        text=prompts[field],
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(EditProfile.waiting_for_new_value, F.text)
async def save_new_field_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field_to_update = data["editing_field"]
    new_value = message.text

    await update_user_field(message.from_user.id, field_to_update, new_value)

    try:
        await message.delete()
    except Exception:
        pass


    text = "Дані успішно збережно"
    builder = InlineKeyboardBuilder()
    builder.button(text="Продовжити", callback_data="profile", style="primary")

    await message.answer(text, reply_markup=builder.as_markup())
    await state.clear()