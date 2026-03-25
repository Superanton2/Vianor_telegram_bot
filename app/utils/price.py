from aiogram import Bot
from app.db.db_requests import get_car_by_number, get_all_admins

import traceback
import gspread

import os
from dotenv import load_dotenv

load_dotenv()
PRICE_SHEET_NAME = os.getenv("PRICE_SHEET_NAME")
SHEET_URL = os.getenv("SHEET_URL")

try:
    gc = gspread.service_account(filename='credentials.json')
    sheet = gc.open_by_url(SHEET_URL).sheet1

    PRICES_CACHE = sheet.get_all_records()
    print("✅ Ціни успішно завантажені з Google Sheets")
except Exception as e:
    print(f"❌ Помилка підключення до Google Sheets: {e}")
    traceback.print_exc()
    PRICES_CACHE = []


async def get_price(car_type: str, service_type: str) -> str:
    if not PRICES_CACHE:
        return "Помилка бази цін "

    car_mapping = {
        "passenger": "легковий",
        "off_roader": "позашляховик",
        "van": "мінівен / бус"
    }
    service_mapping = {
        "Безконтактна мийка": "безконтактна мийка",
        "Пилосос": "пилосос",
        "Комплекс": "комплекс"
    }

    target_car_column = car_mapping.get(car_type, car_type)
    target_service_row = service_mapping.get(service_type, service_type).lower()

    for row in PRICES_CACHE:
        current_service = str(row.get('послуга', '')).lower()
        if current_service == target_service_row:
            price = row.get(target_car_column)
            if price is not None and price != '':
                return str(price)

    return "Ціну не знайдено "


async def check_price_updates(bot: Bot):
    global PRICES_CACHE

    try:
        new_prices = sheet.get_all_records()
    except Exception as e:
        print(f"Помилка перевірки цін: {e}")
        return

    if new_prices != PRICES_CACHE:
        PRICES_CACHE = new_prices

        admins = await get_all_admins()
        text = "⚠️ <b>Увага!</b> Ціни в Google Таблиці були оновлені. Бот вже використовує нові тарифи."

        for admin in admins:
            try:
                await bot.send_message(chat_id=admin.telegram_id, text=text)
            except Exception as e:
                print(f"Не вдалося відправити повідомлення адміну {admin.telegram_id}: {e}")