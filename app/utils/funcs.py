from aiogram import types
from aiogram.exceptions import TelegramBadRequest

async def safe_reply(message: types.Message, text: str, reply_markup=None):
    try:
        return await message.edit_text(text=text, reply_markup=reply_markup,
                                        parse_mode="HTML", disable_web_page_preview=True)
    except TelegramBadRequest:
        return await message.answer(text=text, reply_markup=reply_markup, parse_mode="HTML",
                                    disable_web_page_preview=True)

def get_car_emoji(car_type: str) -> str:
    if car_type == "passenger":
        return "🚗"
    elif car_type == "off_roader":
        return "🚙"
    elif car_type == "van":
        return "🚐"
    else:
        return " "

def get_service_emoji(service:str) -> str:
    if service == "Безконтактна мийка":
        return "💦"
    elif service == "Мийка, Пилосос":
        return "🧹"
    elif service == "Комплекс":
        return "✨"
    else:
        return "🧽"