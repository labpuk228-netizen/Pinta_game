from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import create_player, get_player, update_online
from keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    player = await get_player(user_id)
    if not player:
        code = await create_player(user_id, message.from_user.username or "player")
        await message.answer(
            f"🎮 Добро пожаловать в Пихту!\n\n"
            f"Твой личный код для переводов: `{code}`\n"
            f"Сохрани его — по нему другие игроки смогут отправлять тебе монеты.\n\n"
            f"Стартовый баланс: 1000 монет 💰",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        await update_online(user_id)
        await message.answer("С возвращением в Пихту! 🌲", reply_markup=main_menu())
