from aiogram import Router, F
from aiogram.types import Message

from database import get_player

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала напиши /start")
        return
    code, balance, job_salary, last_online = player[2], player[3], player[4], player[5]
    await message.answer(
        f"👤 **Твой профиль**\n\n"
        f"🆔 Личный код: `{code}`\n"
        f"💰 Баланс: {balance} монет\n"
        f"💼 Зарплата: {job_salary} монет/цикл\n"
        f"🕒 Последний вход: {last_online}",
        parse_mode="Markdown"
    )
