import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.db.db_setup import init_db

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.utils.price import check_price_updates

import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN_ID = os.getenv("MAIN_ADMIN_ID")
WHEN_TO_UPDATE_PRICES = os.getenv("WHEN_TO_UPDATE_PRICES").split(':')[0]

from app.routers.controller_router import router as controller_router


async def main():
    # Start bot instants
    bot = Bot(
       token=BOT_TOKEN,
       default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Start scheduler for price monitoring
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(
        check_price_updates,
        trigger='cron',
        hour=WHEN_TO_UPDATE_PRICES,
        minute=0,
        kwargs={'bot': bot}
    )
    scheduler.start()

    dp = Dispatcher()
    dp.include_router(controller_router)

    # sleep so bd can initialise
    await asyncio.sleep(5)

    # start db
    print("start db")
    await init_db()

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