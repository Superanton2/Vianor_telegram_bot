from aiogram import Router, F, types
router = Router()


@router.callback_query(F.data == "enroll")
async def show_faq(callback: types.CallbackQuery):

    await callback.message.answer("Це запис")
    await callback.answer()