import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

from app.db.PostgreSQL import AsyncSessionLocal, init_models
from app.db.middlewares import DbSessionMiddleware
from app.routers.controller_router import router as controller_router

async def main():
   # Start bot instants
   bot = Bot(
       token=TOKEN,
       default = DefaultBotProperties(parse_mode=ParseMode.HTML)
   )

   dp = Dispatcher()
   dp.include_router(controller_router)


   dp.update.middleware(DbSessionMiddleware(session_pool=AsyncSessionLocal))
   print("Ініціалізація бази даних...")
   await init_models()

   # And the run events dispatching
   print("Start bot")
   await dp.start_polling(bot)


if __name__ == "__main__":
   # to see information about working with the bot
   logging.basicConfig(level=logging.INFO, stream=sys.stdout)

   try:
       asyncio.run(main())
   except KeyboardInterrupt:
       print("Bot stopped")