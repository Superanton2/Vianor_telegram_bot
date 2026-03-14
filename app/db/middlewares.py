from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Відкриваємо сесію
        async with self.session_pool() as session:
            # Кладемо сесію в словник data, щоб вона була доступна в хендлері
            data["session"] = session
            try:
                # Передаємо управління хендлеру
                return await handler(event, data)
            except Exception as e:
                # Якщо в хендлері сталася помилка - відкочуємо зміни в БД
                await session.rollback()
                raise e
            finally:
                # Сесія автоматично закриється при виході з блоку async with
                pass