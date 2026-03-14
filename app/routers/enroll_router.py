from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.callback_query(F.data == "enroll")
async def show_faq(callback: types.CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    builder = InlineKeyboardBuilder()

    builder.button(text="Назад", callback_data="controller_hub", style = "primary")

    await callback.message.answer("Це запис", reply_markup=builder.as_markup())
    await callback.answer()