import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer

# 1. Створюємо підключення (URL: postgresql+asyncpg://user:password@host:port/db_name)
engine = create_async_engine("postgresql+asyncpg://admin:secret@localhost:5432/carwash_db", echo=True)

# 2. Фабрика сесій (через них ми робим запити)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# 3. Базовий клас для таблиць
class Base(DeclarativeBase):
    pass


# 4. Приклад таблиці "Юзери"
class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String, nullable=True)


# 5. Функція створення таблиць (запускається при старті бота)
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

from app.db.models import Base
# ... твій існуючий код з engine та AsyncSessionLocal ...

async def init_models():
    # Ця функція створить таблиці, якщо їх ще немає
    async with engine.begin() as conn:
        # run_sync використовується, бо create_all - це синхронна операція під капотом
        await conn.run_sync(Base.metadata.create_all)