import aiosqlite, random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_player, DB_PATH, is_in_prison
from keyboards import crime_menu

router = Router()

@router.message(F.text.contains("Криминал"))
async def crime_hub(message: Message, state: FSMContext):
    await state.clear() 
    player = await get_player(message.from_user.id)
    
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        # ВАЖНО: Отправляем меню, чтобы была кнопка "Выйти из тюрьмы"
        await message.answer(
            f"⛓ Ты в тюрьме! Осталось: {mins} мин.\nНажми «⚖️ Выйти из тюрьмы», чтобы внести залог.",
            reply_markup=crime_menu()
        )
        return
        
    lockpicks = "✅ Есть" if player[25] == 1 else "❌ Нет"
    hacker_sw = "✅ Есть" if player[26] == 1 else "❌ Нет"
    sec_status = "✅ Есть" if player[24] == 1 else "❌ Нет"
    
    await message.answer(
        f"🕵️ **Теневой рынок**\n\n"
        f"🛡 Охрана: {sec_status}\n"
        f"🔓 Отмычки: {lockpicks}\n"
        f"💻 Хакерский софт: {hacker_sw}\n"
        f"🏅 Репутация: {player[17]}\n\n"
        f"Выбери действие снизу:", 
        parse_mode="Markdown", reply_markup=crime_menu()
    )

@router.message(F.text.contains("Черный рынок"))
async def black_market(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить Отмычки (1000💰)", callback_data="crimebuy_lockpicks")],
        [InlineKeyboardButton(text="Купить Хакерский софт (5000💰)", callback_data="crimebuy_hacker")],
        [InlineKeyboardButton(text="Купить Охрану (5000💰)", callback_data="crimebuy_security")]
    ])
    await message.answer("🛒 **Черный рынок**\n\nЗдесь продаются инструменты для незаконных дел. Без них кражи невозможны!", reply_markup=kb)

@router.callback_query(F.data.startswith("crimebuy_"))
async def buy_crime_item(callback: CallbackQuery):
    item = callback.data.split("_")[1]
    player = await get_player(callback.from_user.id)
    
    costs = {"lockpicks": 1000, "hacker": 5000, "security": 5000}
    cost = costs.get(item)
    
    if player[3] < cost:
        await callback.message.answer(f"❌ Недостаточно монет! Нужно {cost}.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        if item == "lockpicks":
            if player[25] == 1: return await callback.message.answer("✅ У тебя уже есть отмычки.")
            await db.execute("UPDATE players SET balance = balance - ?, has_lockpicks = 1 WHERE user_id=?", (cost, callback.from_user.id))
            text = "🔓 Куплены отмычки!"
        elif item == "hacker":
            if player[26] == 1: return await callback.message.answer("✅ У тебя уже есть хакерский софт.")
            await db.execute("UPDATE players SET balance = balance - ?, has_hacker_software = 1 WHERE user_id=?", (cost, callback.from_user.id))
            text = "💻 Куплен хакерский софт!"
        elif item == "security":
            if player[24] == 1: return await callback.message.answer("✅ У тебя уже есть охрана.")
            await db.execute("UPDATE players SET balance = balance - ?, has_security = 1 WHERE user_id=?", (cost, callback.from_user.id))
            text = "🛡 Охрана нанята!"
            
        await db.commit()
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(F.text.contains("Ограбить игрока"))
async def try_rob(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
        
    player = await get_player(message.from_user.id)
    if player[25] == 0:
        await message.answer("❌ У тебя нет отмычек! Купи их на Черном рынке.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, balance, has_security FROM players WHERE user_id != ? AND balance > 100", (message.from_user.id,)) as cur:
            victims = await cur.fetchall()
    if not victims:
        await message.answer("В городе нет подходящих целей.")
        return
        
    victim_id, victim_balance, victim_sec = random.choice(victims)
    success_chance = 0.2 if victim_sec == 1 else 0.6
    
    async with aiosqlite.connect(DB_PATH) as db:
        if random.random() < success_chance:
            stolen = int(victim_balance * random.uniform(0.05, 0.15))
            await db.execute("UPDATE players SET balance = balance - ?, reputation = reputation - 5 WHERE user_id=?", (stolen, victim_id))
            await db.execute("UPDATE players SET balance = balance + ?, reputation = reputation - 5 WHERE user_id=?", (stolen, message.from_user.id))
            try: await message.bot.send_message(victim_id, f"🚨 **Тревога!** Тебя ограбили! Неизвестный украл {stolen} монет.")
            except: pass
            await message.answer(f"🦹 Успех! Ты выкрал **{stolen}** монет. (Репутация -5)")
        else:
            prison_until = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=?, reputation = reputation - 15, has_lockpicks = 0 WHERE user_id=?", (prison_until, message.from_user.id))
            if victim_sec == 1:
                try: await message.bot.send_message(victim_id, "🛡 Твоя охрана задержала вора! Он отправлен в тюрьму.")
                except: pass
            await message.answer("🚔 Провал! Тебя поймали. Тюрьма на 15 минут. (Репутация -15, Отмычки изъяты)")
        await db.commit()

@router.message(F.text.contains("Ограбить NPC"))
async def rob_npc(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        if random.random() < 0.7: 
            stolen = random.randint(100, 400)
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
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
        
    player = await get_player(message.from_user.id)
    if player[26] == 0:
        await message.answer("❌ У тебя нет хакерского софта! Купи его на Черном рынке.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        if random.random() < 0.3: 
            stolen = random.randint(10000, 30000)
            await db.execute("UPDATE players SET balance = balance + ?, reputation = reputation - 20 WHERE user_id=?", (stolen, message.from_user.id))
            text = f"💻 **ДЖЕКПОТ!** Ты взломал банк и перевел **{stolen}** монет на свой счет! (Репутация -20)"
        else:
            prison_until = (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE players SET in_prison_until=?, reputation = reputation - 30, has_hacker_software = 0 WHERE user_id=?", (prison_until, message.from_user.id))
            text = "🚔 **ПРОВАЛ!** Киберполиция отследила твой IP. Тюрьма на 30 минут. (Репутация -30, Софт уничтожен)"
        await db.commit()
    await message.answer(text)

@router.message(F.text.contains("Выйти из тюрьмы"))
async def out_of_jail(message: Message):
    player = await get_player(message.from_user.id)
    if not player[18] or player[18] == "None":
        await message.answer("Ты не в тюрьме.")
        return
        
    # Проверяем, истек ли срок
    try:
        prison_time = datetime.strptime(player[18], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() >= prison_time:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE players SET in_prison_until=NULL WHERE user_id=?", (message.from_user.id,))
                await db.commit()
            await message.answer("⏳ Твой срок уже истек, ты свободен!")
            return
    except: pass
        
    if player[3] < 2000:
        await message.answer("❌ Залог стоит 2000 монет. У тебя нет таких денег, жди конца срока.")
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
