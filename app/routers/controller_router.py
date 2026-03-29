from dotenv import load_dotenv

from aiogram import F
from aiogram.filters import Command
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

import app.utils.keyboards as kb
from app.utils.funcs import safe_reply
from app.db.db_requests import is_user_in_role, get_user, get_user_active_bookings

from app.routers.faq_router import router as faq_router
from app.routers.booking_router import router as booking_router
from app.routers.registration_router import router as registration_router
from app.routers.profile_router import router as profile_router
from app.routers.my_booking_router import router as my_booking_router
from app.routers.admin_staff_manage import router as admin_router

load_dotenv()
router = Router()
router.include_routers(
    faq_router,
    booking_router,
    registration_router,
    profile_router,
    my_booking_router,
    admin_router,
)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = kb.create_main_user_keyboard()

    tg_id = message.from_user.id
    if await is_user_in_role(tg_id, "user"):
        active_bookings = await get_user_active_bookings(tg_id)
        text = ("👋Привіт!\nЯ бот для запису на мийку vianor. \n"
                "Обирай дію, я допоможу тобі тут з усім\n")
        keyboard = kb.create_main_user_keyboard(has_booking=bool(active_bookings))
    elif await is_user_in_role(tg_id, "worker"):
        text = "Вітаю worker"
    elif await is_user_in_role(tg_id, "admin"):
        text = "Привіт admin"
        keyboard=  kb.create_main_admin_keyboard()

    else:
        text = "Вітаю новий користувач"
        keyboard = kb.create_main_user_keyboard(is_new=True)

    await message.reply(
        text= text,
        reply_markup= keyboard.as_markup()
    )

@router.callback_query(F.data.in_(["controller_hub", "controller_hub_new"]))
async def cmd_back_hub(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await state.clear()

    tg_id = callback.from_user.id
    if await is_user_in_role(tg_id, "user"):
        text = "👋Обери наступну дію:"
        active_bookings = await get_user_active_bookings(tg_id)
        keyboard = kb.create_main_user_keyboard(has_booking=bool(active_bookings))

    elif await is_user_in_role(tg_id, "worker"):
        text = "Вітаю worker"
    elif await is_user_in_role(tg_id, "admin"):
        text = "Привіт admin"
        keyboard=  kb.create_main_admin_keyboard()


    if callback.data == "controller_hub_new":
        await safe_reply(
            message=callback.message,
            text=text,
            reply_markup=keyboard.as_markup()
        )
    else:
        await callback.message.answer(
            text=text,
            reply_markup=keyboard.as_markup()
        )

    await callback.answer()