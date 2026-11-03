import random
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH
from keyboards import section_menu

router = Router()

@router.message(F.text == "🎲 Фортуна")
async def fortune(message: Message):
    player = await get_player(message.from_user.id)
    last = player[10]

    if last:
        last_time = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() - last_time < timedelta(minutes=10):
            rem = timedelta(minutes=10) - (datetime.utcnow() - last_time)
            await message.answer(f"🎲 Казино закрыто. Жди {int(rem.total_seconds()//60)} мин.")
            return

    roll = random.randint(1, 100)
    if roll <= 40:
        amount = random.randint(50, 200)
        text = f"📉 Неудача! Ты потерял {amount} монет."
        change = -amount
    elif roll <= 90:
        amount = random.randint(100, 500)
        text = f"📈 Удача! Ты нашел {amount} монет."
        change = amount
    else:
        amount = random.randint(1000, 3000)
        text = f"💎 ДЖЕКПОТ! {amount} монет!"
        change = amount

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ?, last_fortune = CURRENT_TIMESTAMP WHERE user_id=?", (change, message.from_user.id))
        await db.commit()
    
    await message.answer(text, reply_markup=section_menu())
