import aiosqlite, random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH
from keyboards import crime_menu

router = Router()

@router.message(F.text.contains("Криминал"))
async def crime_hub(message: Message):
    player = await get_player(message.from_user.id)
    
    if player[18] and player[18] != "None":
        try:
            prison_time = datetime.strptime(player[18], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() < prison_time:
                rem = prison_time - datetime.utcnow()
                await message.answer(f"⛓ Ты в тюрьме! Осталось: {int(rem.total_seconds()//60)} мин.\nНажми «⚖️ Выйти из тюрьмы», чтобы внести залог.")
                return
        except: pass
        
    sec_status = "✅ Куплена" if player[24] == 1 else "❌ Нет"
    await message.answer(
        f"🕵️ **Теневой рынок**\n\n"
        f"Твоя охрана: {sec_status}\n"
        f"Твоя репутация: {player[17]} (чем ниже, тем хуже берут на работу)\n\n"
        f"Выбери действие снизу:", 
        parse_mode="Markdown", reply_markup=crime_menu()
    )

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
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, balance, has_security FROM players WHERE user_id != ? AND balance > 100", (message.from_user.id,)) as cur:
            victims = await cur.fetchall()
    if not victims:
        await message.answer("В городе нет подходящих целей.")
        return
        
    victim_id, victim_balance, victim_sec = random.choice(victims)
    success_chance = 0.1 if victim_sec == 1 else 0.5
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 500 WHERE user_id=?", (message.from_user.id,))
        if random.random() < success_chance:
            stolen = int(victim_balance * random.uniform(0.05, 0.15))
            await db.execute("UPDATE players SET balance = balance - ?, reputation = reputation - 5 WHERE user_id=?", (stolen, victim_id))
            await db.execute("UPDATE players SET balance = balance + ?, reputation = reputation - 5 WHERE user_id=?", (stolen, message.from_user.id))
            try: await message.bot.send_message(victim_id, f"🚨 **Тревога!** Тебя ограбили! Неизвестный украл {stolen} монет.")
            except: pass
            await message.answer(f"🦹 Успех! Ты выкрал **{stolen}** монет. (Репутация -5)")
        else:
            prison_until = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=?, reputation = reputation - 15 WHERE user_id=?", (prison_until, message.from_user.id))
            if victim_sec == 1:
                try: await message.bot.send_message(victim_id, "🛡 Твоя охрана задержала вора! Он отправлен в тюрьму.")
                except: pass
            await message.answer("🚔 Провал! Тебя поймали. Тюрьма на 15 минут. (Репутация -15)")
        await db.commit()

@router.message(F.text.contains("Ограбить NPC"))
async def rob_npc(message: Message):
    player = await get_player(message.from_user.id)
    if player[3] < 200:
        await message.answer("❌ Нужно 200 монет на подготовку.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 200 WHERE user_id=?", (message.from_user.id,))
        if random.random() < 0.7:
            stolen = random.randint(300, 1000)
            await db.execute("UPDATE players SET balance = balance + ?, reputation = reputation - 2 WHERE user_id=?", (stolen, message.from_user.id))
            text = f"👤 Ты ограбил случайного прохожего и забрал **{stolen}** монет! (Репутация -2)"
        else:
            prison_until = (datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=?, reputation = reputation - 10 WHERE user_id=?", (prison_until, message.from_user.id))
            text = "🚔 Провал! Прохожий оказался полицейским. Тюрьма на 10 минут. (Репутация -10)"
        await db.commit()
    await message.answer(text)

@router.message(F.text.contains("Взломать банк"))
async def hack_bank(message: Message):
    player = await get_player(message.from_user.id)
    if player[3] < 5000:
        await message.answer("❌ Для взлома нужен хакерский софт (стоит 5000).")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 5000 WHERE user_id=?", (message.from_user.id,))
        if random.random() < 0.3:
            stolen = random.randint(10000, 30000)
            await db.execute("UPDATE players SET balance = balance + ?, reputation = reputation - 20 WHERE user_id=?", (stolen, message.from_user.id))
            text = f"💻 **ДЖЕКПОТ!** Ты взломал банк и перевел **{stolen}** монет на свой счет! (Репутация -20)"
        else:
            prison_until = (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=?, reputation = reputation - 30 WHERE user_id=?", (prison_until, message.from_user.id))
            text = "🚔 **ПРОВАЛ!** Киберполиция отследила твой IP. Тюрьма на 30 минут. (Репутация -30)"
        await db.commit()
    await message.answer(text)

@router.message(F.text.contains("Выйти из тюрьмы"))
async def out_of_jail(message: Message):
    player = await get_player(message.from_user.id)
    if not player[18]:
        await message.answer("Ты не в тюрьме.")
        return
        
    if player[3] < 2000:
        await message.answer("❌ Залог стоит 2000 монет. У тебя нет таких денег.")
        return
        
    if random.random() < 0.3:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET balance = balance - 2000 WHERE user_id=?", (message.from_user.id,))
            await db.commit()
        await message.answer("🚨 Адвокат взял деньги, но полиция отказалась брать взятку! Деньги потеряны, жди срок.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 2000, in_prison_until=NULL WHERE user_id=?", (message.from_user.id,))
        await db.commit()
    await message.answer("⚖️ Залог внесен. Ты на свободе!")
