from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import app.db.db_requests as db
from app.utils.funcs import UKR_DAYS
from app.utils.keyboards import get_days_keyboard
from app.utils.google_sheets import sync_staff_to_sheets, log_staff_action



import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS").split(",")]

router = Router()

class WorkerStates(StatesGroup):
    waiting_for_worker_id = State()
    waiting_for_worker_name = State()
    waiting_for_worker_phone = State()
    waiting_for_worker_days = State()


@router.callback_query(F.data == "add_worker")
async def add_worker_step1(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await state.set_state(WorkerStates.waiting_for_worker_id)

    builder = ReplyKeyboardBuilder()
    builder.button(
        text="👤 Обрати користувача",
        request_user=types.KeyboardButtonRequestUser(request_id=1, user_is_bot=False)
    )
    builder.button(text="Скасувати")
    builder.adjust(1)

    new_msg = await callback.message.answer(
        "[1/5] Надішліть ID нового працівника або натисніть кнопку <b>'👤 Обрати користувача'</b> нижче:",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )

    await state.update_data(step1_msg_id=new_msg.message_id)
    await callback.answer()


@router.message(WorkerStates.waiting_for_worker_id)
async def add_worker_step2(message: types.Message, state: FSMContext):
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

    new_worker_id = None
    if message.user_shared:
        new_worker_id = message.user_shared.user_id
    elif message.text and message.text.isdigit():
        new_worker_id = int(message.text)

    if not new_worker_id:
        await message.answer("⚠️ Це не схоже на ID. Спробуйте ще раз або натисніть 'Скасувати'.")
        return

    if await db.is_user_in_role(new_worker_id, "worker"):
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

        await message.answer("❌Ця людина вже є працівником", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()
        from app.routers.admin_routers.admin_staff_router import staff_manage_menu
        await staff_manage_menu(message)
        return


    await state.update_data(new_worker_id=new_worker_id)
    await state.set_state(WorkerStates.waiting_for_worker_name)

    try:
        await message.delete()
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
    except Exception:
        pass

    new_msg = await message.answer(
        f"[2/5] ID <code>{new_worker_id}</code> отримано. Введіть ім'я для цього працівника:",
        reply_markup=types.ForceReply(input_field_placeholder="Введіть ім'я прцівника", selective=True),
        parse_mode="HTML"
    )
    await state.update_data(step2_msg_id=new_msg.message_id)


@router.message(WorkerStates.waiting_for_worker_name, F.text)
async def add_worker_step3(message: types.Message, state: FSMContext):
    worker_name = message.text
    data = await state.get_data()
    prev_msg_id = data.get("step2_msg_id")

    await state.update_data(worker_name=worker_name)

    try:
        await message.delete()
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
    except Exception:
        pass

    new_msg = await message.answer(
        "[3/5] Введіть номер телефону нового працівника:",
        reply_markup=types.ForceReply(input_field_placeholder="Введіть телефон", selective=True)
    )
    await state.update_data(step3_msg_id=new_msg.message_id)
    await state.set_state(WorkerStates.waiting_for_worker_phone)


@router.message(WorkerStates.waiting_for_worker_phone, F.text)
async def add_worker_step4(message: types.Message, state: FSMContext):
    worker_phone = message.text
    data = await state.get_data()
    prev_msg_id = data.get("step3_msg_id")

    await state.update_data(worker_phone=worker_phone, work_days=[])

    try:
        await message.delete()
        await message.bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
    except Exception:
        pass

    markup = get_days_keyboard([])
    new_msg = await message.answer(
        "[4/5] Оберіть коли новий працівник буде працювати. Якщо нажати один раз, то варіант вибереться. "
        "Якщо нажати ще раз, то варіант прибиреться:",
        reply_markup=markup.as_markup()
    )
    await state.update_data(step4_msg_id=new_msg.message_id)
    await state.set_state(WorkerStates.waiting_for_worker_days)


@router.callback_query(WorkerStates.waiting_for_worker_days, F.data.startswith("w_day_"))
async def toggle_worker_day(callback: types.CallbackQuery, state: FSMContext):
    day_index = int(callback.data.split("_")[2])
    data = await state.get_data()
    work_days = data.get("work_days", [])

    if day_index in work_days:
        # await callback.answer("⚠️ Цей день прибрано з робочого графіка!", show_alert=True)
        work_days.remove(day_index)
    else:
        work_days.append(day_index)
        await callback.answer()

    await state.update_data(work_days=work_days)

    markup = get_days_keyboard(work_days)
    await callback.message.edit_reply_markup(reply_markup=markup.as_markup())


@router.callback_query(WorkerStates.waiting_for_worker_days, F.data == "w_days_done")
async def add_worker_step5(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_worker_id = data.get("new_worker_id")
    worker_name = data.get("worker_name")
    worker_phone = data.get("worker_phone")
    work_days = data.get("work_days", [])

    work_days.sort()
    days_str = ", ".join([UKR_DAYS[d] for d in work_days]) if work_days else "Не обрано"

    builder = InlineKeyboardBuilder()
    builder.button(text="Підтвердити", callback_data="confirm_add_worker", style="success")
    builder.button(text="Скасувати", callback_data="cancel_add_worker_inline", style="danger")
    builder.adjust(1)

    await callback.message.edit_text(
        f"[5/5] 📋 <b>Перевірте дані нового працівника:</b>\n\n"
        f"👤 Ім'я: <a href='tg://user?id={new_worker_id}'>{worker_name}</a>\n"
        f"📱 Телефон: <code>{worker_phone}</code>\n"
        f"📅 Робочі дні: {days_str}\n\n"
        f"Підтверджуєте додавання?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_add_worker_inline")
async def cancel_add_worker_inline(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌Ви скасували запис. Нікого не було додано.", reply_markup=None)
    await state.clear()

    from app.routers.admin_routers.admin_staff_router import staff_manage_menu
    await staff_manage_menu(callback)

    await callback.answer()


@router.callback_query(F.data == "confirm_add_worker")
async def confirm_add_worker(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_worker_id = data.get("new_worker_id")
    worker_name = data.get("worker_name")
    worker_phone = data.get("worker_phone")
    work_days = data.get("work_days", [])
    days_str = ", ".join([UKR_DAYS[d] for d in work_days]) if work_days else "Не обрано"


    try:
        await db.add_worker(
            tg_id=new_worker_id,
            name=worker_name,
            phone=worker_phone,
            work_days=work_days
        )

        asyncio.create_task(sync_staff_to_sheets())
        action_text = f"Додав працівника: {worker_name} ({new_worker_id})"
        asyncio.create_task(log_staff_action(
            who_did_it=callback.from_user.full_name,
            action_desc=action_text
        ))

    except Exception as e:
        await callback.message.edit_text(f"❌ Виникла помилка БД: {e}")
        await state.clear()
        return

    text = (f"[5/5] ✅ <b>Добавлено нового працівника:</b>\n\n"
        f"👤 Ім'я: <a href='tg://user?id={new_worker_id}'>{worker_name}</a>\n"
        f"📱 Телефон: <code>{worker_phone}</code>\n"
        f"📅 Робочі дні: {days_str}\n\n"
        f"Підтверджуєте додавання?")

    await callback.message.edit_text(
        text= text,
        parse_mode="HTML",
        reply_markup=None
    )


    adder_name = callback.from_user.full_name
    for super_admin in SUPER_ADMINS:
        try:
            await callback.bot.send_message(
                chat_id=int(super_admin),
                text=f"ℹ️ <b>Лог безпеки</b>\n{adder_name} додав нового працівника: "
                     f"<a href='tg://user?id={new_worker_id}'>{worker_name}</a>.",
                parse_mode="HTML"
            )
        except Exception:
            pass


    await state.clear()

    from app.routers.admin_routers.admin_staff_router import staff_manage_menu
    await staff_manage_menu(callback)

    await callback.answer()