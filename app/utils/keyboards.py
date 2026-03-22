from aiogram.utils.keyboard import InlineKeyboardBuilder

def create_main_user_keyboard(is_new: bool= False):
    builder = InlineKeyboardBuilder()

    if is_new:
        builder.button(text="Зареєструватись", callback_data="registration")
    else:
        builder.button(text="Записатись", callback_data="booking")
        builder.button(text="👤 Мій профіль", callback_data="profile")
        builder.button(text="❓ Часті Питання", callback_data="questions")


    builder.adjust(1)
    return builder

def create_main_worker_keyboard():
    pass

def create_main_admin_keyboard():
    pass