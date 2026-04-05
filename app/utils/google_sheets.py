import gspread
import asyncio
import os
from datetime import datetime
from sqlalchemy import select
from app.db.db_setup import engine, admin_list, worker_list
from dotenv import load_dotenv

load_dotenv()


def get_sheet():
    gc = gspread.service_account(filename='credentials.json')
    return gc.open(os.getenv("LOG_SHEET_NAME"))


def _sync_staff_sync(admin_data: list, worker_data: list):
    """Синхронна функція для запису даних через gspread"""
    sh = get_sheet()

    ws_admins = sh.worksheet("Admins")
    ws_admins.batch_clear(["A2:C1000"])

    if admin_data:
        ws_admins.update(range_name="A2", values=admin_data)

    ws_workers = sh.worksheet("Workers")
    ws_workers.batch_clear(["A2:E1000"])

    if worker_data:
        ws_workers.update(range_name="A2", values=worker_data)


async def sync_staff_to_sheets():
    """Асинхронний виклик оновлення списків персоналу"""
    admin_rows = []
    worker_rows = []

    async with engine.begin() as conn:
        admins_result = await conn.execute(select(admin_list))
        admins = list(admins_result.fetchall())

        workers_result = await conn.execute(select(worker_list))
        workers = list(workers_result.fetchall())

    admins.sort(key=lambda x: x.is_active, reverse=True)
    workers.sort(key=lambda x: x.is_active, reverse=True)

    for a in admins:
        status = "Активний" if a.is_active else "Деактивований"
        admin_rows.append([a.name, str(a.telegram_id), status])


    days_map = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"}

    for w in workers:
        status = "Активний" if w.is_active else "Деактивований"

        if w.work_days:
            days = ", ".join([days_map[day] for day in w.work_days])
        else:
            days = "Немає"

        worker_rows.append([w.name, str(w.telegram_id), w.phone, days, status])

    await asyncio.to_thread(_sync_staff_sync, admin_rows, worker_rows)


def _append_row_sync(sheet_name: str, row_data: list):
    sh = get_sheet()
    ws = sh.worksheet(sheet_name)
    ws.append_row(row_data)


async def add_user_to_sheet(tg_id: int, name: str, phone: str, user_type: str):
    """Додає нового клієнта в таблицю"""
    try:
        row = [str(tg_id), name, phone, user_type]
        await asyncio.to_thread(_append_row_sync, "Users", row)
        print(f"✅ Юзера {name} успішно додано в Sheets!")
    except Exception as e:
        print(f"❌ ПОМИЛКА додавання юзера в Sheets: {e}")

async def add_car_to_sheet(car_number: str, car_type: str, tg_id: int):
    """Додає нову машину в таблицю"""
    try:
        row = [car_number, car_type, str(tg_id)]
        await asyncio.to_thread(_append_row_sync, "Cars", row)
        print(f"✅ Машину {car_number} успішно додано в Sheets!")
    except Exception as e:
        print(f"❌ ПОМИЛКА додавання машини в Sheets: {e}")


def _append_log_sync(date_time: str, who: str, action: str):
    """Синхронна функція для додавання логу в зворотньому порядку (завжди на лист Admins)"""
    sh = get_sheet()
    ws = sh.worksheet("Admins")

    # 1. Читаємо всі існуючі логи (від F2 до H і до самого низу)
    try:
        existing_logs = ws.get("F2:H")
    except Exception:
        existing_logs = []

        # 2. Формуємо новий запис
    new_log = [[date_time, who, action]]

    # 3. Ставимо новий лог ЗВЕРХУ, а всі старі додаємо під ним
    updated_logs = new_log + existing_logs

    # 4. Записуємо весь масив логів назад у таблицю
    end_row = len(updated_logs) + 1
    ws.update(range_name=f"F2:H{end_row}", values=updated_logs)


async def log_staff_action(who_did_it: str, action_desc: str):
    """Асинхронний виклик для логування (всі події пишуться в Admins)"""
    # Беремо поточний час і форматуємо: "День.Місяць.Рік Година:Хвилина"
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    await asyncio.to_thread(_append_log_sync, now, who_did_it, action_desc)



def _get_prices_from_sheet_sync():
    """Синхронно зчитує ціни з аркуша Prices"""
    sh = get_sheet()
    ws = sh.worksheet("Prices")
    data = ws.get_all_values()[1:] # Отримуємо всі дані, пропускаючи заголовок (рядок 1)

    prices_data = []
    for row in data:
        if not row[0]: continue  # Пропускаємо порожні рядки
        prices_data.append({
            "service": row[0],
            "sedan": int(row[1]),
            "suv": int(row[2]),
            "minivan": int(row[3])
        })
    return prices_data


async def sync_prices_to_db():
    """Отримує ціни з таблиці та оновлює їх у вашій системі (БД або локальний файл)"""
    prices = await asyncio.to_thread(_get_prices_from_sheet_sync)

    # ТУТ ЛОГІКА ОНОВЛЕННЯ В БД
    # Наприклад, якщо у тебе є таблиця в БД для цін, ти можеш її очистити і записати нові
    # Або просто повернути цей список для подальшої обробки
    return prices



def _update_user_sync(tg_id: str, field: str, new_value: str):
    """Синхронно шукає юзера за ID і оновлює ім'я або телефон"""
    sh = get_sheet()
    ws = sh.worksheet("Users")
    try:
        # Шукаємо ID у першій колонці
        cell = ws.find(str(tg_id), in_column=1)
        if cell:
            if field == "name":
                ws.update(range_name=f"B{cell.row}", values=[[new_value]]) # Колонка B - Ім'я
            elif field == "phone":
                ws.update(range_name=f"C{cell.row}", values=[[new_value]]) # Колонка C - Телефон
    except Exception as e:
        print(f"Помилка оновлення юзера в Sheets: {e}")

async def update_user_in_sheet(tg_id: int, field: str, new_value: str):
    """field може бути 'name' або 'phone'"""
    await asyncio.to_thread(_update_user_sync, str(tg_id), field, new_value)


def _delete_car_sync(car_number: str):
    """Синхронно шукає машину за номером і видаляє рядок"""
    sh = get_sheet()
    ws = sh.worksheet("Cars")
    try:
        cell = ws.find(car_number, in_column=1)
        if cell:
            ws.delete_rows(cell.row)
    except Exception:
        pass

async def delete_car_from_sheet(car_number: str):
    await asyncio.to_thread(_delete_car_sync, car_number)


def _add_booking_sync(booking_data: list):
    """Синхронна функція запису бронювання (найновіші зверху)"""
    sh = get_sheet()
    ws = sh.worksheet("Bookings")

    # 1. Читаємо поточні записи (з A2 по H, щоб не чіпати формули в I та J)
    try:
        # Обмежуємо колонкою H, бо в I та J у нас ARRAYFORMULA
        existing_data = ws.get("A2:H")
    except Exception:
        existing_data = []

    # 2. Новий запис ставимо на початок
    updated_data = [booking_data] + existing_data

    # 3. Визначаємо діапазон для запису
    end_row = len(updated_data) + 1
    ws.update(range_name=f"A2:H{end_row}", values=updated_data)


async def add_booking_to_sheet(booking_id: int, b_date, b_time, car_number: str,
                               service: str, price: int, worker_name: str):
    """
    Асинхронна обгортка для логування мийки
    # Структура: ID | Дата | Час | Номер авто | Послуга | Працівник | Ціна | Статус
    """

    # Форматуємо дату та час для таблиці
    date_str = b_date.strftime("%d.%m.%Y") if hasattr(b_date, 'strftime') else str(b_date)
    time_str = b_time.strftime("%H:%M") if hasattr(b_time, 'strftime') else str(b_time)

    row = [booking_id, date_str, time_str, car_number, service, worker_name, price, "Призначено"]

    await asyncio.to_thread(_add_booking_sync, row)