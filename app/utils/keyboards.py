from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.funcs import get_car_emoji, UKR_DAYS

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
        builder.button(text="👥 Менеджмент персоналу", callback_data="admin_staff_manage_new")
        builder.button(text="📊 Google табличка", callback_data="admin_archive")
        builder.button(text="❓Часта питання", callback_data="questions_new")

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

def create_admin_staff_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Додати адміна", callback_data="add_admin")
    builder.button(text="👥 Додати працівника", callback_data="add_worker")
    builder.button(text="🛡️Керування доступом", callback_data="permission_control")

    builder.button(text="Назад", callback_data="controller_hub", style="primary")
    builder.adjust(1)

    return builder

def get_days_keyboard(selected_days: list) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    for i, day in enumerate(UKR_DAYS):
        if i in selected_days:
            builder.button(text=day, callback_data=f"w_day_{i}", style="success")
        else:
            builder.button(text=day, callback_data=f"w_day_{i}")

    builder.adjust(3, 3, 1)  # По 3 дні в ряд + неділя окремо
    builder.button(text="Продовжити", callback_data="w_days_done", style="primary")
    return builder