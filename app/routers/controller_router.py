from dotenv import load_dotenv

from aiogram import F, types, Router
from aiogram.filters import Command

from app.utils.keyboards import create_main_keyboard

from aiogram import Router, types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User

router = Router()
load_dotenv()


@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):

    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    is_user = result.scalar_one_or_none()
    keyboard = create_main_keyboard()
    text = ("👋Привіт!\nЯ бот для запису на мийку vianor. \n"
            "Обирай дію, я допоможу тобі тут з усім\n")

    if not is_user:
        new_user = User(telegram_id=message.from_user.id, full_name=message.from_user.full_name)
        session.add(new_user)
        await session.commit()

        text += "Новий юзер"
        await message.answer(
            text= text,
            reply_markup= keyboard.as_markup()
        )
    else:
        await message.reply(
            text= text,
            reply_markup= keyboard.as_markup()
        )
