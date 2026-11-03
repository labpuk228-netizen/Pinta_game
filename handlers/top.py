import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import DB_PATH

router = Router()

# Ловим разные варианты написания кнопки
@router.message(F.text.in_(["🏆 Топ", "Топ", "🏆 Топ игроков", "Топ игроков"]))
async def show_top(message: Message):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Берем только тех, у кого есть имя и баланс больше нуля
            async with db.execute("SELECT COALESCE(username, 'Игрок') as name, COALESCE(balance, 0) FROM players WHERE balance IS NOT NULL ORDER BY balance DESC LIMIT 5") as cur:
                rich = await cur.fetchall()
                
            async with db.execute("SELECT COALESCE(username, 'Игрок') as name, COALESCE(business_level, 1) FROM players WHERE business_id > 0 ORDER BY business_level DESC LIMIT 5") as cur:
                biz = await cur.fetchall()

        text = "🏆 **Зал Славы**\n\n"
        
        text += "💰 **Самые богатые:**\n"
        if rich:
            for i, r in enumerate(rich, 1):
                name = f"@{r[0]}" if r[0] not in ["Игрок", "player", "None", "none"] else str(r[0])
                text += f"{i}. {name} — {r[1]} монет\n"
        else:
            text += "Пока нет данных.\n"
            
        text += "\n🏢 **Лучшие бизнесмены:**\n"
        if biz:
            for i, b in enumerate(biz, 1):
                name = f"@{b[0]}" if b[0] not in ["Игрок", "player", "None", "none"] else str(b[0])
                text += f"{i}. {name} — Уровень {b[1]}\n"
        else:
            text += "Пока нет бизнесов.\n"
            
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке топа: {e}")
