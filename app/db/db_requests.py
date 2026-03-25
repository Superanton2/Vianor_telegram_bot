import datetime

from sqlalchemy import select, insert, update, func
from app.db.db_setup import engine, bookings, admin_list, worker_list, user_list, cars

import os
from dotenv import load_dotenv

load_dotenv()
DAYS_TO_BOOK_LIMIT = int(os.getenv("DAYS_TO_BOOK_LIMIT"))

async def add_user(tg_id: int, user_type: str, name: str = None, phone: str = None) -> None:
    """
    add user to db
    :param tg_id: telegram id of user
    :param user_type: 'individual' or 'business'
    :param name: Ures name
    :param phone: +380 ...
    :return: None
    """
    async with engine.begin() as conn:
        insert_statement = insert(user_list).values(
            telegram_id=tg_id,
            type=user_type,
            name=name,
            phone=phone
        )
        await conn.execute(insert_statement)

async def add_car(tg_id: int, car_number: str, car_type: str) -> None:
    """
    Add car to db
    :param tg_id: telegram id of user
    :param car_number: car number 'AA1234BB'
    :param car_type: 'passenger' / 'off_roader' / 'van'
    :return:
    """
    async with engine.begin() as conn:
        insert_statement = insert(cars).values(
            car_number=car_number,
            type=car_type,
            user_id=tg_id
        )
        await conn.execute(insert_statement)

async def get_user(tg_id: int):
    """
    Fing user data in db
    :param tg_id:
    :return: User data or None is there are no user in db
    """
    async with engine.begin() as conn:
        select_statement = select(user_list).where(user_list.c.telegram_id == tg_id)
        result = await conn.execute(select_statement)
        return result.fetchone()

async def update_user_field(tg_id: int, field_name: str, new_value: str) -> None:
    """
    update particular field in user db
    :param tg_id: id of user
    :param field_name: field to change. Have to be 'name', 'phone' or 'car_number'
    :param new_value: value to write
    :return: None
    """
    async with engine.begin() as conn:
        update_data = {field_name: new_value}

        update_statement = (
            update(user_list)
            .where(user_list.c.telegram_id == tg_id)
            .values(**update_data)
        )
        await conn.execute(update_statement)

async def add_booking(tg_id: int, b_date, b_time, service: str) -> None:
    """
    add booking time to db
    :param tg_id: id of user
    :param b_date: date of booking
    :param b_time: time of booking
    :param service: type of service (cleaner/complex)
    :return: None
    """
    async with engine.begin() as conn:
        insert_statement = insert(bookings).values(
            user_id=tg_id,
            date=b_date,
            time=b_time,
            service=service
        )
        await conn.execute(insert_statement)

async def add_admin_or_worker(tg_id: int, role: str, work_days: list[int],
                              name: str = None, phone: str = None) -> None:
    """
    add admin or worker to db
    :param tg_id: telegram id of admin or worker
    :param role: 'admin' or 'worker'
    :param name: name
    :param phone: new admin phone +380 ...
    :param work_days: days when worker works. from 0 (Mon) to 6 (Sun)
    :return: None
    """
    async with engine.begin() as conn:
        insert_statement = insert(admin_list).values(
            telegram_id=tg_id,
            role= role,
            name=name,
            phone=phone,
            work_days= work_days,
        )
        await conn.execute(insert_statement)

async def get_workers_by_day(day_index: int):
    """
    finds all workers for particular day using day index
    :param day_index: from 0 (Mon) to 6 (Sun)
    :return:
    """
    async with engine.begin() as conn:
        select_statement = select(admin_list).where(admin_list.c.work_days.any(day_index))
        result = await conn.execute(select_statement)
        return result.fetchall()

async def is_user_in_role(tg_id: int, role: str) -> bool:
    """
    find if telegram id is in database 'type'
    :param tg_id: telegram id of admin or worker or user
    :param type: admin / worker / user
    :return:
    """

    if role == "admin":
        db = admin_list
    elif role == "worker":
        db = worker_list
    elif role == "user":
        db = user_list
    else:
        raise Exception(f"No such type. You have to use 'admin', 'worker' or 'user'"
                        f"Your type was: {role}")

    async with engine.begin() as conn:
        select_statement = select(db).where(db.c.telegram_id == tg_id)
        result = await conn.execute(select_statement)

        row = result.fetchone()

        if row is not None:
            return True
        else:
            return False

async def get_booked_times(target_date: datetime.date) -> list[str]:
    """
    find booked time slots in particular date

    :param target_date: date were to find
    :return: list of booked hours for concrete date in form ["10:00", "14:00"]
    """
    async with engine.begin() as conn:
        select_statement = select(bookings.c.time).where(
            (bookings.c.date == target_date) &
            (bookings.c.status == "active")
        )
        result = await conn.execute(select_statement)

        return [row[0].strftime("%H:%M") for row in result.fetchall()]

async def check_if_day_full(target_date: datetime.date, total_slots: int) -> bool:
    """
    Перевіряє, чи кількість активних записів на день дорівнює або перевищує
    загальну кількість робочих годин.
    """
    async with engine.begin() as conn:
        # Використовуємо SQL COUNT для швидкого підрахунку
        select_statement = select(func.count()).select_from(bookings).where(
            (bookings.c.date == target_date) &
            (bookings.c.status == "active")
        )
        result = await conn.execute(select_statement)
        count = result.scalar()

        return count >= total_slots

async def get_user_cars(tg_id: int):
    """
    Повертає список автомобілів користувача
    """
    async with engine.begin() as conn:
        select_statement = select(cars).where(cars.c.user_id == tg_id)
        result = await conn.execute(select_statement)
        return result.fetchall()

async def add_booking(tg_id: int, b_date, b_time, service: str, car_number: str) -> None:
    """
    Створює запис на мийку з прив'язкою до авто
    """
    async with engine.begin() as conn:
        insert_statement = insert(bookings).values(
            date=b_date,
            time=b_time,
            service=service,
            user_id=tg_id,
            car_number=car_number,
            status="active"
        )
        await conn.execute(insert_statement)

async def get_car_by_number(car_number: str):
    """
    Повертає об'єкт автомобіля з БД за його номером.
    """
    async with engine.begin() as conn:
        select_statement = select(cars).where(cars.c.car_number == car_number)
        result = await conn.execute(select_statement)
        return result.fetchone()

async def get_all_admins():
    """
    Повертає список всіх адміністраторів з БД
    """
    async with engine.begin() as conn:
        select_statement = select(admin_list)
        result = await conn.execute(select_statement)
        return result.fetchall()

async def get_active_booking_for_car(car_number: str, days_limit: int = DAYS_TO_BOOK_LIMIT):
    """
    Перевіряє, чи є активний запис для машини на найближчі N днів.
    Повертає об'єкт запису, якщо є, інакше None.
    """
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days_limit)

    async with engine.begin() as conn:
        select_statement = select(bookings).where(
            (bookings.c.car_number == car_number) &
            (bookings.c.status == "active") &
            (bookings.c.date >= today) &
            (bookings.c.date <= end_date)
        )
        result = await conn.execute(select_statement)
        return result.fetchone()