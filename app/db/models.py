from datetime import date, time
from sqlalchemy import BigInteger, String, Date, Time, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # Telegram ID може бути дуже великим, тому ОБОВ'ЯЗКОВО BigInteger
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    # Роль: 'user', 'admin' або 'washer'
    role: Mapped[str] = mapped_column(String, default="user")

    # Зв'язок з таблицею записів (один юзер може мати багато записів)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)

    # Дані з твого макета: машина, номер, день, час
    car_info: Mapped[str] = mapped_column(String, nullable=False)  # Напр., "Audi, сіра, КА1234АХ"
    book_date: Mapped[date] = mapped_column(Date, nullable=False)
    book_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Зв'язок назад до юзера
    user: Mapped["User"] = relationship(back_populates="bookings")

    # Захист від овербукінгу на рівні БД:
    # Не можна створити два записи на одну й ту саму дату і час
    __table_args__ = (
        UniqueConstraint('book_date', 'book_time', name='uix_date_time'),
    )