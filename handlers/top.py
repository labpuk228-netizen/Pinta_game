import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import DB_PATH

router = Router()

@router.message(F.text.contains("Топ"))
async def show_top(message: Message):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COALESCE(username, 'Игрок') as name, COALESCE(balance, 0) FROM players WHERE balance IS NOT NULL ORDER BY balance DESC LIMIT 5") as cur:
                rich = await cur.fetchall()
                
            # Ищем топ по количеству бизнесов
            sql = "SELECT COALESCE(p.username, 'Игрок') as name, COUNT(pb.id) as b_count FROM players p JOIN player_businesses pb ON p.user_id = pb.user_id GROUP BY p.user_id ORDER BY b_count DESC LIMIT 5"
            async with db.execute(sql) as cur:
                biz = await cur.fetchall()

        text = "🏆 <b>Зал Славы</b>\n\n"
        
        text += "💰 <b>Самые богатые:</b>\n"
        if rich:
            for i, r in enumerate(rich, 1):
                name = f"@{r[0]}" if r[0] not in ["Игрок", "player", "None", "none"] else str(r[0])
                text += f"{i}. {name} — {r[1]} монет\n"
        else:
            text += "Пока нет данных.\n"
            
        text += "\n🏢 <b>Лучшие бизнесмены (по кол-ву):</b>\n"
        if biz:
            for i, b in enumerate(biz, 1):
                name = f"@{b[0]}" if b[0] not in ["Игрок", "player", "None", "none"] else str(b[0])
                text += f"{i}. {name} — Бизнесов: {b[1]}\n"
        else:
            text += "Пока нет бизнесов.\n"
            
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке топа: {e}")
