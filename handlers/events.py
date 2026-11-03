import random
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🎲 Фортуна")
async def fortune(message: Message):
    player = await get_player(message.from_user.id)
    last_fortune = player[11] if len(player) > 11 else None

    if last_fortune:
        last_time = datetime.strptime(last_fortune, "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        if now - last_time < timedelta(minutes=10):
            time_left = timedelta(minutes=10) - (now - last_time)
            minutes = int(time_left.total_seconds() // 60)
            await message.answer(f"🎲 Казино закрыто на перерыв. Приходи через {minutes} мин.")
            return

    roll = random.randint(1, 100)
    
    if roll <= 40:
        amount = random.randint(50, 200)
        text = f"📉 Неудача! Ты потерял {amount} монет (украли в толпе)."
        change = -amount
    elif roll <= 90:
        amount = random.randint(100, 500)
        text = f"📈 Удача! Ты нашел {amount} монет на улице."
        change = amount
    else:
        amount = random.randint(1000, 3000)
        text = f"💎 ДЖЕКПОТ! Ты сорвал куш в лотерею: {amount} монет!"
        change = amount

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ?, last_fortune = CURRENT_TIMESTAMP WHERE user_id=?", (change, message.from_user.id))
        await db.commit()
    
    await message.answer(text)
