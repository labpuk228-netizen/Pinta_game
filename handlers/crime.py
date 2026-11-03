import aiosqlite, random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import crime_menu

router = Router()

@router.message(F.text.contains("Криминал"))
async def crime_hub(message: Message):
    player = await get_player(message.from_user.id)
    
    # Проверка на тюрьму
    if player[18] and player[18] != "None":
        try:
            prison_time = datetime.strptime(player[18], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() < prison_time:
                rem = prison_time - datetime.utcnow()
                await message.answer(f"⛓ Ты в тюрьме! Осталось: {int(rem.total_seconds()//60)} мин.\nНажми «⚖️ Выйти из тюрьмы», чтобы заплатить залог.")
                return
        except: pass
        
    sec_status = "✅ Куплена" if player[24] == 1 else "❌ Нет"
    await message.answer(f"🕵️ **Теневой рынок**\n\nТвоя охрана: {sec_status}\n\nВыбери действие снизу (осторожно, кражи преследуются по закону!).", parse_mode="Markdown", reply_markup=crime_menu())

@router.message(F.text.contains("Купить охрану"))
async def buy_security(message: Message):
    player = await get_player(message.from_user.id)
    if player[24] == 1:
        await message.answer("✅ У тебя уже есть охрана!")
        return
    if player[3] < 5000:
        await message.answer("❌ Охрана стоит 5000 монет. У тебя недостаточно средств.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 5000, has_security = 1 WHERE user_id=?", (message.from_user.id,))
        await db.commit()
    await message.answer("🛡 Охрана нанята! Теперь тебя будет крайне сложно ограбить.")

@router.message(F.text.contains("Ограбить игрока"))
async def try_rob(message: Message):
    player = await get_player(message.from_user.id)
    if player[3] < 500:
        await message.answer("❌ Для подготовки к краже нужны отмычки (стоят 500 монет).")
        return
        
    # Ищем случайную жертву
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, balance, has_security FROM players WHERE user_id != ? AND balance > 100", (message.from_user.id,)) as cur:
            victims = await cur.fetchall()
            
    if not victims:
        await message.answer("В городе нет подходящих целей.")
        return
        
    victim = random.choice(victims)
    victim_id, victim_balance, victim_sec = victim
    
    # Шанс успеха: 50% (если у жертвы нет охраны), 10% (если есть)
    success_chance = 0.1 if victim_sec == 1 else 0.5
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 500 WHERE user_id=?", (message.from_user.id,)) # Трата на отмычки
        
        if random.random() < success_chance:
            # Успех
            stolen = int(victim_balance * random.uniform(0.05, 0.15))
            await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (stolen, victim_id))
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (stolen, message.from_user.id))
            
            # Уведомляем жертву (если у нее есть охрана или просто как факт)
            try:
                await message.bot.send_message(victim_id, f"🚨 **Тревога!** Тебя ограбили! Неизвестный украл {stolen} монет.")
            except: pass
            
            await message.answer(f"🦹 Успех! Ты незаметно выкрал **{stolen}** монет из кармана жертвы.")
        else:
            # Провал и тюрьма
            prison_until = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=? WHERE user_id=?", (prison_until, message.from_user.id))
            
            if victim_sec == 1:
                try: await message.bot.send_message(victim_id, "🛡 Твоя охрана задержала вора! Он отправлен в тюрьму.")
                except: pass
                
            await message.answer("🚔 Провал! Тебя поймала полиция. Ты отправлен в тюрьму на 15 минут.")
            
        await db.commit()

@router.message(F.text.contains("Выйти из тюрьмы"))
async def out_of_jail(message: Message):
    player = await get_player(message.from_user.id)
    if not player[18]:
        await message.answer("Ты не в тюрьме.")
        return
        
    if player[3] < 2000:
        await message.answer("❌ Залог адвокату стоит 2000 монет. У тебя нет таких денег, придется сидеть.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 2000, in_prison_until=NULL WHERE user_id=?", (message.from_user.id,))
        await db.commit()
    await message.answer("⚖️ Адвокат внес залог. Ты на свободе!")
