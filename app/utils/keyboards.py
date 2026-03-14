from aiogram.utils.keyboard import InlineKeyboardBuilder

def create_main_keyboard(admin: bool= False) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    builder.button( text="Записатись", callback_data="enroll")
    builder.button( text="❓ Часті Питання", callback_data="questions")

    if admin:
        builder.button( text="🔐 Панель Адміна", callback_data="admin_hub")

    builder.adjust(1)
    return builder
