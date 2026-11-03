import random
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import casino_menu

router = Router()

@router.message(F.text.contains("Казино"))
async def casino_hub(message: Message):
    await message.answer("🎲 **Добро пожаловать в казино!**\n\nВыбери игру снизу.", reply_markup=casino_menu())

@router.message(F.text.contains("Рулетка"))
async def roulette_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roul_red")],
        [InlineKeyboardButton(text="⚫ Черное (x2)", callback_data="roul_black")],
        [InlineKeyboardButton(text="🟢 Зеро (x14)", callback_data="roul_zero")]
    ])
    await message.answer("🎰 **Рулетка**\nВведи сумму ставки в чат, а затем выбери цвет:", reply_markup=kb)
    await message.answer("Ставка будет равна введенному числу.")

@router.callback_query(F.data.startswith("roul_"))
async def play_roulette(callback: CallbackQuery):
    bet = 100
    player = await get_player(callback.from_user.id)
    if player[3] < bet:
        await callback.message.answer("❌ Недостаточно монет!")
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
async def dice_game(message: Message):
    await message.answer("🎲 **Кости**\n\nОтправь боту стикер с кубиком (или напиши /dice), и если выпадет 5 или 6 — ты выиграешь 300 монет, иначе потеряешь 100.")

@router.message(F.dice)
async def handle_dice(message: Message):
    if message.dice.value >= 5:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET balance = balance + 300 WHERE user_id=?", (message.from_user.id,))
            await db.commit()
        await message.answer("🎉 Победа! Ты выиграл 300 монет!")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET balance = balance - 100 WHERE user_id=?", (message.from_user.id,))
            await db.commit()
        await message.answer("😢 Не повезло. Ты потерял 100 монет.")
