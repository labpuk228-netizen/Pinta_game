import random
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_player, DB_PATH
from keyboards import casino_menu
from states import CasinoState, DiceState

router = Router()

@router.message(F.text.contains("Казино"))
async def casino_hub(message: Message):
    await message.answer("🎲 **Добро пожаловать в казино!**\n\nВыбери игру снизу.", reply_markup=casino_menu())

# --- РУЛЕТКА ---
@router.message(F.text.contains("Рулетка"))
async def ask_roulette_bet(message: Message, state: FSMContext):
    await state.set_state(CasinoState.waiting_bet)
    await message.answer("🎰 **Рулетка**\n\nВведи сумму, которую хочешь поставить:")

@router.message(CasinoState.waiting_bet)
async def process_roulette_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи целое число больше нуля.")
        return
    
    player = await get_player(message.from_user.id)
    if player[3] < bet:
        await message.answer(f"❌ Недостаточно монет! У тебя только {player[3]}.")
        await state.clear()
        return
        
    await state.update_data(bet=bet)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roul_red")],
        [InlineKeyboardButton(text="⚫ Черное (x2)", callback_data="roul_black")],
        [InlineKeyboardButton(text="🟢 Зеро (x14)", callback_data="roul_zero")]
    ])
    await message.answer(f"Ставка: **{bet}** монет.\nВыбери цвет:", parse_mode="Markdown", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data.startswith("roul_"))
async def play_roulette(callback: CallbackQuery):
    try:
        bet = int(callback.message.text.split("Ставка: **")[1].split("**")[0])
    except:
        await callback.answer("Ошибка ставки. Начни заново.", show_alert=False)
        return

    player = await get_player(callback.from_user.id)
    if player[3] < bet:
        await callback.message.edit_text("❌ Недостаточно монет!")
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

# --- КОСТИ ---
@router.message(F.text.contains("Кости"))
async def ask_dice_bet(message: Message, state: FSMContext):
    await state.set_state(DiceState.waiting_bet)
    await message.answer("🎲 **Кости**\n\nВведи сумму ставки (выигрыш x2, если выпадет 5 или 6):")

@router.message(DiceState.waiting_bet)
async def process_dice_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи целое число больше нуля.")
        return
        
    player = await get_player(message.from_user.id)
    if player[3] < bet:
        await message.answer(f"❌ Недостаточно монет! У тебя только {player[3]}.")
        await state.clear()
        return
        
    await state.update_data(bet=bet)
    await state.set_state(None)
    await message.answer(f"Ставка **{bet}** принята!\nОтправь стикер с кубиком 🎲:", parse_mode="Markdown")

@router.message(F.dice)
async def handle_dice(message: Message, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 100)
    
    if message.dice.value >= 5:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (bet * 2, message.from_user.id))
            await db.commit()
        await message.answer(f"🎉 Победа! Выпало {message.dice.value}. Ты выиграл {bet * 2} монет!")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (bet, message.from_user.id))
            await db.commit()
        await message.answer(f"😢 Не повезло (выпало {message.dice.value}). Ты потерял {bet} монет.")
    await state.clear()
