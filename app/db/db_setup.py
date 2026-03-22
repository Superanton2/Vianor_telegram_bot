from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData, Table, Column, Integer, BigInteger, String, Date, Time, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import select, insert

import os
from dotenv import load_dotenv

load_dotenv()
BD_ENGINE = os.getenv("BD_ENGINE")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID"))
work_hours_str = os.getenv("WORK_HOURS")
WORK_HOURS = [hour.strip() for hour in work_hours_str.split(",")]
engine = create_async_engine(BD_ENGINE, echo=False)
meta = MetaData()

admin_list = Table(
    "admin_list",
    meta,
    Column("telegram_id", BigInteger, primary_key=True),
    Column("name", String, nullable=False),
)

worker_list = Table(
    "worker_list",
    meta,
Column("telegram_id", BigInteger, primary_key=True),
    Column("name", String, nullable=False),
    Column("phone", String),
    Column("work_days", ARRAY(Integer), nullable=True), # 0 - Mon / 6 - Sun
)

user_list = Table(
    "user_list",
    meta,
    Column("telegram_id", BigInteger, primary_key=True),
    Column("type", String, nullable=False), # 'individual' or 'business'
    Column("name", String, nullable=False),
    Column("phone", String, nullable=False),
)

bookings = Table(
    "bookings",
    meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=False),
    Column("time", Time, nullable=False),
    Column("service", String),
    Column("user_id", BigInteger, ForeignKey('user_list.telegram_id')),
    Column("status", String, default="active"),
    Column("car_number", String, ForeignKey('cars.car_number'))
)

cars = Table(
    "cars",
    meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("car_number", String, nullable=False, unique=True), # AA1234BB
    Column("type", String, nullable=False), # 'passenger' / 'off_roader' / 'van'
    Column("user_id", BigInteger, ForeignKey('user_list.telegram_id')) # car owner
)

async def init_db():
    """
    database initialization. Start of all tables
    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)

        # if no admins
        check_admins = await conn.execute(select(admin_list))
        if check_admins.fetchone() is None:

            insert_statement = insert(admin_list).values(telegram_id=MAIN_ADMIN_ID, name="Anton")
            await conn.execute(insert_statement)
