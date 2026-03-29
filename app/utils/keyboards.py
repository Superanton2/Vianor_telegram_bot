from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.funcs import get_car_emoji

def create_main_user_keyboard(is_new: bool= False, has_booking: bool= False) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    if is_new:
        builder.button(text="Зареєструватись", callback_data="registration")
    else:
        if has_booking:
            builder.button(text="🗓 Мій запис", callback_data="my_bookings_menu")
        builder.button(text="📅 Записатись", callback_data="booking")

        builder.button(text="👤 Мій профіль", callback_data="profile")
        builder.button(text="❓ Часті Питання", callback_data="questions_new")


    builder.adjust(1)
    return builder

def create_main_worker_keyboard():
    pass

def create_main_admin_keyboard() -> InlineKeyboardBuilder:
        builder = InlineKeyboardBuilder()
        builder.button(text="👥 Менеджмент персоналу", callback_data="admin_staff_manage")
        builder.button(text="📦 Архів", callback_data="admin_archive")
        builder.button(text="💰 Коригування ціни", callback_data="admin_price_edit")

        builder.adjust(1)
        return builder

def create_cars_keyboard(user_cars) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    for car in user_cars:
        c_type = {"passenger": "Легковий", "off_roader": "Позашляховик", "van": "Мінівен/Бус"}.get(car.type, car.type)

        car_emoji = get_car_emoji(car.type)

        btn_text = f"{car_emoji} {car.car_number} ({c_type})"
        builder.button(text=btn_text, callback_data=f"book_car_{car.car_number}")

    builder.button(text="Назад", callback_data="controller_hub_new", style="primary")
    builder.adjust(1)

    return builder