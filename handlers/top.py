import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import DB_PATH

router = Router()

@router.message(F.text.contains("Топ"))
async def show_top(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        # Используем COALESCE, чтобы не было ошибок, если username пустой
        async with db.execute("SELECT COALESCE(username, 'Игрок') as name, balance FROM players ORDER BY balance DESC LIMIT 5") as cur:
            rich = await cur.fetchall()
            
        async with db.execute("SELECT COALESCE(username, 'Игрок') as name, business_level FROM players WHERE business_id > 0 ORDER BY business_level DESC LIMIT 5") as cur:
            biz = await cur.fetchall()

    text = "🏆 **Зал Славы**\n\n"
    
    text += "💰 **Самые богатые:**\n"
    if rich:
        for i, r in enumerate(rich, 1):
            name = f"@{r[0]}" if r[0] != "Игрок" and r[0] != "player" else r[0]
            text += f"{i}. {name} — {r[1]} монет\n"
    else:
        text += "Пока нет данных.\n"
        
    text += "\n🏢 **Лучшие бизнесмены:**\n"
    if biz:
        for i, b in enumerate(biz, 1):
            name = f"@{b[0]}" if b[0] != "Игрок" and b[0] != "player" else b[0]
            text += f"{i}. {name} — Уровень {b[1]}\n"
    else:
        text += "Пока нет бизнесов.\n"
        
    await message.answer(text, parse_mode="Markdown")
