from aiogram import types
from aiogram.exceptions import TelegramBadRequest

import app.db.db_requests as db

UKR_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

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

async def get_admin_staff_text() -> str:
    text = "Унравління персоналом\n\n"
    admins = await db.get_all_admins()
    if not admins:
        text += "Список адміністраторів порожній."
    else:
        text += "🔑 <b>Список адміністраторів:</b>:\n"
        for admin in admins:
            text += f"- <a href='tg://user?id={admin.telegram_id}'>{admin.name}</a>\n"

        text += "───────────────\n"

    workers = await db.get_all_workers()
    if not workers:
        text += "Список працівників пустий\n"
    else:
        # text += "🛠 <b>Список працівників:</b>:\n"
        text += "👥 <b>Список працівників:</b>:\n"
        for worker in workers:
            text += f"- <a href='tg://user?id={worker.telegram_id}'>{worker.name}</a>\n"
            if worker.work_days:

                days_str = ", ".join([UKR_DAYS[day] for day in worker.work_days])
                text += f"📅 Робочі дні: {days_str}\n"
            else:
                text += "📅 Робочі дні: не призначено\n"

        text += "───────────────\n"

    return text