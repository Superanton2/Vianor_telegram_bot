from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData, Table, Column, Integer, BigInteger, String, Date, Time, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import select, insert

import os
from dotenv import load_dotenv

load_dotenv()
BD_ENGINE = os.getenv("BD_ENGINE")
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS").split(",")]
work_hours_str = os.getenv("WORK_HOURS")
WORK_HOURS = [hour.strip() for hour in work_hours_str.split(",")]
engine = create_async_engine(BD_ENGINE, echo=False)
meta = MetaData()

admin_list = Table(
    "admin_list",
    meta,
    Column("telegram_id", BigInteger, primary_key=True),
    Column("name", String, nullable=False),
    Column("is_active", Boolean, default=True)
)

worker_list = Table(
    "worker_list",
    meta,
Column("telegram_id", BigInteger, primary_key=True),
    Column("name", String, nullable=False),
    Column("phone", String),
    Column("work_days", ARRAY(Integer), nullable=True), # 0 - Mon / 6 - Sun
    Column("is_active", Boolean, default=True)
)

user_list = Table(
    "user_list",
    meta,
    Column("telegram_id", BigInteger, primary_key=True),
    Column("type", String, nullable=False), # 'individual' or 'business'
    Column("name", String, nullable=False),
    Column("phone", String, nullable=False),
)

cars = Table(
    "cars",
    meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("car_number", String, nullable=False, unique=True), # AA1234BB
    Column("type", String, nullable=False), # 'passenger' / 'off_roader' / 'van'
    Column("user_id", BigInteger, ForeignKey('user_list.telegram_id')) # car owner
)

bookings = Table(
    "bookings",
    meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=False),
    Column("time", Time, nullable=False),
    Column("service", String),
    Column("price", Integer),
    Column("status", String, default="active"),
    Column("user_id", BigInteger, ForeignKey('user_list.telegram_id')),
    Column("car_number", String, ForeignKey('cars.car_number'))
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

            insert_statement1 = insert(admin_list).values(telegram_id=SUPER_ADMINS[0], name="Anton")
            insert_statement2 = insert(admin_list).values(telegram_id=SUPER_ADMINS[1], name="Ігор")
            await conn.execute(insert_statement1)
            await conn.execute(insert_statement2)
