from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import app.db.db_requests as db
from app.utils.funcs import log_to_sheets

import os
from dotenv import load_dotenv

load_dotenv()
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS").split(",")]

router = Router()

class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_admin_name = State()


@router.callback_query(F.data == "add_admin")
async def add_admin_step1(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await state.set_state(AdminStates.waiting_for_admin_id)

    builder = ReplyKeyboardBuilder()
    builder.button(
        text="👤 Обрати користувача",
        request_user=types.KeyboardButtonRequestUser(request_id=1, user_is_bot=False)
    )
    builder.button(text="Скасувати")
    builder.adjust(1)

    new_msg = await callback.message.answer(
        "[1/3] Надішліть ID нового адміністратора або натисніть кнопку <b>'👤 Обрати користувача'</b> нижче:",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )

    await state.update_data(step1_msg_id=new_msg.message_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_admin_id)
async def add_admin_step2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prev_msg_id = data.get("step1_msg_id")

    if message.text == "Скасувати":
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=prev_msg_id
            )
        except Exception:
            pass

        await message.answer("❌Ви скасували запис. Нікого не було додано", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()
        from app.routers.admin_routers.admin_staff_router import staff_manage_menu
        await staff_manage_menu(message)
        return

    new_admin_id = None
    if message.user_shared:
        new_admin_id = message.user_shared.user_id
    elif message.text and message.text.isdigit():
        new_admin_id = int(message.text)

    if not new_admin_id:
        await message.answer("⚠️ Це не схоже на ID. Спробуйте ще раз або натисніть 'Скасувати'.")
        return

    if await db.is_user_in_role(new_admin_id, "admin"):
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=prev_msg_id
            )
        except Exception:
            pass

        await message.answer("❌Ця людина вже є адміністратором", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()
        from app.routers.admin_routers.admin_staff_router import staff_manage_menu
        await staff_manage_menu(message)
        return

        # try:
        #     await message.delete()
        #     await message.bot.edit_message_text(
        #         chat_id=message.chat.id,
        #         message_id=prev_msg_id,
        #         text="❌ Цей користувач вже є адміністратором."
        #     )
        # except Exception:
        #     pass
        # await state.clear()
        # from app.routers.admin_routers.admin_staff_router import staff_manage_menu
        # await staff_manage_menu(message)
        # return

    await state.update_data(new_admin_id=new_admin_id)
    await state.set_state(AdminStates.waiting_for_admin_name)

    try:
        await message.delete()
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
    except Exception:
        pass

    new_msg = await message.answer(
        f"[2/3] ID <code>{new_admin_id}</code> отримано. Введіть ім'я для цього адміністратора:",
        reply_markup=types.ForceReply(input_field_placeholder="Введіть ім'я адміністратора", selective=True),
        parse_mode="HTML"
    )
    await state.update_data(step2_msg_id=new_msg.message_id)


@router.message(AdminStates.waiting_for_admin_name, F.text)
async def add_admin_step3(message: types.Message, state: FSMContext):
    admin_name = message.text
    data = await state.get_data()
    new_admin_id = data.get("new_admin_id")
    prev_msg_id = data.get("step2_msg_id")

    await state.update_data(admin_name=admin_name)

    try:
        await message.delete()
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
    except Exception:
        pass

    builder = InlineKeyboardBuilder()
    builder.button(text="Підтвердити", callback_data="confirm_add_admin", style= "success")
    builder.button(text="Скасувати", callback_data="cancel_add_admin_inline", style="danger")
    builder.adjust(1)

    await message.answer(
        f"[3/3] <a href='tg://user?id={new_admin_id}'>{admin_name}</a> буде добавлено.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_add_admin_inline")
async def cancel_add_admin_inline(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌Ви скасували запис. Нікого не було додано.", reply_markup=None)
    await state.clear()

    from app.routers.admin_routers.admin_staff_router import staff_manage_menu
    await staff_manage_menu(callback)

    await callback.answer()


@router.callback_query(F.data == "confirm_add_admin")
async def confirm_add_admin(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_admin_id = data.get("new_admin_id")
    admin_name = data.get("admin_name")

    try:
        from sqlalchemy import insert
        from app.db.db_setup import engine, admin_list
        async with engine.begin() as conn:
            await conn.execute(insert(admin_list).values(telegram_id=new_admin_id, name=admin_name))
    except Exception as e:
        await callback.message.edit_text(f"❌ Виникла помилка БД: {e}")
        await state.clear()
        return

    await callback.message.edit_text(
        f"<a href='tg://user?id={new_admin_id}'>{admin_name}</a> було добавлено як адміністратора.",
        parse_mode="HTML",
        reply_markup=None
    )


    adder_name = callback.from_user.full_name
    for super_admin in SUPER_ADMINS:
        try:
            await callback.bot.send_message(
                chat_id=int(super_admin),
                text=f"ℹ️ <b>Лог безпеки</b>\n{adder_name} додав нового адміністратора: <a href='tg://user?id={new_admin_id}'>{admin_name}</a>.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    log_text = f"Користувач {adder_name} додав адміністратора {admin_name} (ID: {new_admin_id})"
    await log_to_sheets(log_text)

    await state.clear()

    from app.routers.admin_routers.admin_staff_router import staff_manage_menu
    await staff_manage_menu(callback)

    await callback.answer()