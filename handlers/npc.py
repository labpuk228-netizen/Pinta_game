import aiosqlite, random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_player, DB_PATH

router = Router()

@router.callback_query(F.data.startswith("npc_"))
async def npc_handler(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    player = await get_player(callback.from_user.id)
    
    if action == "no":
        await callback.message.edit_text("Ты проигнорировал сообщение.")
        return
        
    event_type = int(callback.data.split("_")[2])
    
    async with aiosqlite.connect(DB_PATH) as db:
        if event_type == 1: # Взаймы
            if player[3] < 5000:
                await callback.answer("У тебя нет 5000 монет!", show_alert=True)
                return
            await db.execute("UPDATE players SET balance = balance - 5000 WHERE user_id=?", (callback.from_user.id,))
            await db.commit()
            await callback.message.edit_text("💸 Ты дал в долг 5000 монет. (NPC пообещал вернуть завтра, но кто его знает...)")
            
        elif event_type == 2: # Инсайд
            if player[3] < 1000:
                await callback.answer("У тебя нет 1000 монет!", show_alert=True)
                return
            await db.execute("UPDATE players SET balance = balance - 1000 WHERE user_id=?", (callback.from_user.id,))
            # Просто даем шанс на удачу
            if random.random() < 0.7:
                await db.execute("UPDATE crypto_assets SET price = price * 1.2 WHERE symbol='BTC'")
                await callback.message.edit_text("📈 Инсайд сработал! BTC вырос на 20%!")
            else:
                await callback.message.edit_text("📉 Это был фейк... Барон тебя обманул.")
            await db.commit()
            
        elif event_type == 3: # Спор
            # Тут просто выдаем награду за клик (для простоты)
            await db.execute("UPDATE players SET balance = balance + 4000 WHERE user_id=?", (callback.from_user.id,))
            await db.commit()
            await callback.message.edit_text("🥊 Ты принял вызов и выиграл спор! +4000 монет.")

    await callback.answer()
