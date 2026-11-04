from aiogram import Router, F
from aiogram.types import Message
from keyboards import main_menu
from database import get_player

router = Router()

@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message):
    player = await get_player(message.from_user.id)
    is_adm = bool(player[17]) if player and len(player) > 17 else False
    await message.answer("🏠 Главное меню:", reply_markup=main_menu(is_adm))
