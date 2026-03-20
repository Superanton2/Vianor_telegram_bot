from sqlalchemy import select, insert
from app.db.db_setup import engine, bookings, admin_list, worker_list, user_list

async def add_user(tg_id: int, user_type: str, car_num: str, name: str = None, phone: str = None) -> None:
    """
    add user to db
    :param tg_id: telegram id of user
    :param user_type: 'individual' or 'business'
    :param car_num: car number 'AA1234BB'
    :param name: Ures name
    :param phone: +380 ...
    :return: None
    """
    async with engine.begin() as conn:
        insert_statement = insert(user_list).values(
            telegram_id=tg_id,
            type=user_type,
            name=name,
            phone=phone,
            car_number=car_num
        )
        await conn.execute(insert_statement)

async def get_user(tg_id: int) -> str | None:
    """
    Fing user data in db
    :param tg_id:
    :return: User data or None is there are no user in db
    """
    async with engine.begin() as conn:
        select_statement = select(user_list).where(user_list.c.telegram_id == tg_id)
        result = await conn.execute(select_statement)
        print(type(result.fetchone()))
        return result.fetchone()


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