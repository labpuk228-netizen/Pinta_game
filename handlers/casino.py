import random
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_player, DB_PATH, is_in_prison
from keyboards import casino_menu
from states import CasinoState

router = Router()

@router.message(F.text.contains("Казино"))
async def casino_hub(message: Message, state: FSMContext):
    await state.clear()
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Казино закрыто. Осталось: {mins} мин.")
        return
        
    player = await get_player(message.from_user.id)
    await message.answer(
        f"🎲 **Добро пожаловать в казино!**\n\n"
        f"Твоя текущая ставка: **{player[27]}** монет.\n"
        f"Нажми «💵 Изменить ставку», чтобы поменять сумму.", 
        parse_mode="Markdown", reply_markup=casino_menu()
    )

@router.message(F.text.contains("Изменить ставку"))
async def set_bet(message: Message, state: FSMContext):
    await state.set_state(CasinoState.waiting_bet)
    await message.answer("💵 Введи новую сумму ставки (например, 500):")

@router.message(CasinoState.waiting_bet)
async def process_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи целое число больше нуля.")
        return
    
    player = await get_player(message.from_user.id)
    if player[3] < bet:
        await message.answer(f"❌ У тебя нет таких денег! Баланс: {player[3]}.")
        await state.clear()
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET current_bet=? WHERE user_id=?", (bet, message.from_user.id))
        await db.commit()
        
    await state.clear()
    await message.answer(f"✅ Ставка установлена: **{bet}** монет.", reply_markup=casino_menu())

@router.message(F.text.contains("Рулетка"))
async def roulette_menu(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roul_red")],
        [InlineKeyboardButton(text="⚫ Черное (x2)", callback_data="roul_black")],
        [InlineKeyboardButton(text="🟢 Зеро (x14)", callback_data="roul_zero")]
    ])
    await message.answer("🎰 **Рулетка**\nВыбери цвет (сумма ставки берется из настроек):", reply_markup=kb)

@router.callback_query(F.data.startswith("roul_"))
async def play_roulette(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    bet = player[27]
    
    if player[3] < bet:
        await callback.message.edit_text("❌ Недостаточно монет для этой ставки! Измени ставку.")
        return
    
    choice = callback.data.split("_")[1]
    roll = random.randint(0, 36)
    
    if roll == 0: color = "zero"
    elif roll <= 18: color = "red"
    else: color = "black"
    
    win = False
    multiplier = 2
    if choice == color:
        win = True
        if choice == "zero": multiplier = 14
    elif choice == "zero" and color == "zero":
        win = True
        multiplier = 14
        
    async with aiosqlite.connect(DB_PATH) as db:
        if win:
            profit = bet * multiplier
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (profit, callback.from_user.id))
            text = f"🎉 Выпало **{roll} ({color})**. Ты выиграл **{profit}** монет!"
        else:
            await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (bet, callback.from_user.id))
            text = f"😢 Выпало **{roll} ({color})**. Ты проиграл **{bet}** монет."
        await db.commit()
        
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(F.text.contains("Кости"))
async def dice_menu(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    player = await get_player(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="roll_dice")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino_back")]
    ])
    await message.answer(f"🎲 **Кости**\nТвоя ставка: {player[27]}.\nНажми кнопку, чтобы бросить кубик (выигрыш x2 при 5 или 6):", reply_markup=kb)

@router.callback_query(F.data == "roll_dice")
async def play_dice(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    bet = player[27]
    
    if player[3] < bet:
        await callback.message.edit_text("❌ Недостаточно монет для этой ставки!")
        return
        
    roll = random.randint(1, 6)
    
    async with aiosqlite.connect(DB_PATH) as db:
        if roll >= 5:
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (bet * 2, callback.from_user.id))
            text = f"🎲 Выпало **{roll}**!\n🎉 Победа! Ты выиграл **{bet * 2}** монет!"
        else:
            await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (bet, callback.from_user.id))
            text = f"🎲 Выпало **{roll}**.\n😢 Не повезло. Ты потерял **{bet}** монет."
        await db.commit()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить еще раз", callback_data="roll_dice")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino_back")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.message(F.text.contains("Лотерея"))
async def lottery_menu(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM system_state WHERE key='jackpot'") as cur:
            jackpot = int((await cur.fetchone())[0])
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Купить билет (100💰)", callback_data="lottery_ticket")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino_back")]
    ])
    await message.answer(f"🎟 **Лотерея**\n\nТекущий джекпот: **{jackpot}** монет!\nБилет стоит 100 монет. Шанс выигрыша: 5%.", parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data == "lottery_ticket")
async def buy_ticket(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[3] < 100:
        await callback.message.edit_text("❌ Недостаточно монет для покупки билета (нужно 100).")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM system_state WHERE key='jackpot'") as cur:
            jackpot = int((await cur.fetchone())[0])
            
        jackpot += 100 
        await db.execute("UPDATE players SET balance = balance - 100 WHERE user_id=?", (callback.from_user.id,))
        
        if random.random() < 0.05:
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (jackpot, callback.from_user.id))
            await db.execute("UPDATE system_state SET value='10000' WHERE key='jackpot'")
            text = f"🎉 **ДЖЕКПОТ!!!**\nТы выиграл **{jackpot}** монет! Джекпот сброшен до 10000."
        else:
            await db.execute("UPDATE system_state SET value=? WHERE key='jackpot'", (str(jackpot),))
            text = f"😢 Билет не выиграл. Но джекпот вырос до **{jackpot}** монет! Попробуешь еще?"
            
        await db.commit()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Купить билет (100💰)", callback_data="lottery_ticket")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino_back")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "casino_back")
async def casino_back(callback: CallbackQuery):
    try: await callback.message.delete()
    except: pass
    await callback.message.answer("🎲 **Добро пожаловать в казино!**\n\nВыбери игру снизу.", reply_markup=casino_menu())
    await callback.answer()
