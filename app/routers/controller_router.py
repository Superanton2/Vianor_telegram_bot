from dotenv import load_dotenv

from aiogram import F, types, Router
from aiogram.filters import Command

from app.utils.keyboards import create_main_keyboard

router = Router()
load_dotenv()


@router.message(Command("start"))
async def cmd_start(message: types.Message):

    keyboard = create_main_keyboard()
    text = ("👋Привіт!\nЯ бот для запису на мийку vianor. \n"
            "Обирай дію, я допоможу тобі тут з усім")

    await message.reply(
        text= text,
        reply_markup= keyboard.as_markup()
    )
