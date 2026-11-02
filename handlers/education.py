import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🎓 Образование")
async def show_education(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        return
    current_edu = player[8] if len(player) > 8 else 0

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, cost, level FROM educations") as cur:
            edus = await cur.fetchall()

    text = "🎓 **Образование**\n\n"
    text += f"Твой текущий уровень: {current_edu}\n\n"
    for e in edus:
        status = "✅ Изучено" if current_edu >= e[3] else f"Цена: {e[2]} монет"
        text += f"ID: {e[0]} | {e[1]} — {status}\n"
    
    text += "\nЧтобы пройти курс, напиши: `/study 1` (где 1 - ID курса)"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text.startswith("/study "))
async def study(message: Message):
    try:
        edu_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Формат: /study 1")
        return
    
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, cost, level FROM educations WHERE id=?", (edu_id,)) as cur:
            edu = await cur.fetchone()
        
        if not edu:
            await message.answer("Курс не найден.")
            return
        if player[3] < edu[1]:
            await message.answer(f"Недостаточно средств! Нужно {edu[1]} монет.")
            return
        
        await db.execute("UPDATE players SET balance = balance - ?, education_level=? WHERE user_id=?", (edu[1], edu[2], message.from_user.id))
        await db.commit()
    await message.answer(f"🎓 Ты успешно прошел курс: {edu[0]}! Твой уровень образования повышен.")
