import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала напиши /start")
        return
    
    prop_id = player[7] if len(player) > 7 else 0
    edu_level = player[8] if len(player) > 8 else 0

    # Узнаем название жилья
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
            prop_title = prop[0] if prop else "Неизвестно"

    await message.answer(
        f"👤 **Твой профиль**\n\n"
        f"🆔 Личный код: `{player[2]}`\n"
        f"💰 Баланс: {player[3]} монет\n"
        f"💼 Зарплата: {player[4]} монет/цикл\n"
        f"🏠 Жильё: {prop_title}\n"
        f"🎓 Образование: Уровень {edu_level}\n"
        f"🕒 Последний вход: {player[5]}",
        parse_mode="Markdown"
            )
