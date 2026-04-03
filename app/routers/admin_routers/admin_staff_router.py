from aiogram import Router, F, types
from aiogram.fsm.state import StatesGroup, State

from app.utils.funcs import get_admin_staff_text, safe_reply
from app.utils.keyboards import create_admin_staff_keyboard

from app.routers.admin_routers.add_admin_router import router as add_admin_router

import os
from dotenv import load_dotenv

load_dotenv()
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS").split(",")]

router = Router()
router.include_routers(
    add_admin_router,
)

class AdminStates(StatesGroup):
    waiting_for_new_admin = State()
    admin_name = State()

class WorkerStates(StatesGroup):
    waiting_for_new_worker = State()
    worker_name = State()
    worker_work_days = State()
    worker_phone = State()



# @router.callback_query(F.data == "admin_staff_manage")
@router.callback_query(F.data.in_(["admin_staff_manage", "admin_staff_manage_new"]))
async def staff_manage_menu(event: types.CallbackQuery | types.Message):

    is_admin = False
    if event.from_user.id in SUPER_ADMINS:
        is_admin = True

    keyboard = create_admin_staff_keyboard(is_admin)
    text = await get_admin_staff_text()

    if isinstance(event, types.CallbackQuery):
        if event.data == "admin_staff_manage_new":
            await safe_reply(
                message=event.message,
                text=text,
                reply_markup=keyboard.as_markup()
            )
        elif event.data == "admin_staff_manage":
            await event.message.edit_text(
                text=text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        else:
            await event.message.answer(
                text=text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )

    else:
        await event.answer(
            text=text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
