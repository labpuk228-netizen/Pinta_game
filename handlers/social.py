import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import section_menu

router = Router()

@router.message(F.text == "🤝 Социалка")
async def social_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏰 Мой клан", callback_data="clan_info")],
        [InlineKeyboardButton(text="📜 Кредиты", callback_data="loans_info")],
        [InlineKeyboardButton(text="🎁 Подарить монеты", callback_data="gift_info")]
    ])
    await message.answer("🤝 **Социальное меню**\n\nВыбери действие:", parse_mode="Markdown", reply_markup=kb)
    await message.answer("Навигация:", reply_markup=section_menu())

@router.callback_query(F.data == "clan_info")
async def clan_info(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[11] == 0:
        text = "🏰 Ты не в клане. Создать клан? Стоит 5000 монет.\n\nКоманда: /create_clan Название"
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name, bank FROM clans WHERE id=?", (player[11],)) as cur:
                clan = await cur.fetchone()
        text = f"🏰 Клан: **{clan[0]}**\n💰 Банк: {clan[1]}"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(F.text.startswith("/create_clan "))
async def create_clan(message: Message):
    name = message.text.split(" ", 1)[1]
    player = await get_player(message.from_user.id)
    if player[3] < 5000:
        await message.answer("Нужно 5000 монет.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 5000 WHERE user_id=?", (message.from_user.id,))
        await db.execute("INSERT INTO clans (name, leader_id) VALUES (?, ?)", (name, message.from_user.id))
        async with db.execute("SELECT last_insert_rowid()") as cur:
            clan_id = (await cur.fetchone())[0]
        await db.execute("UPDATE players SET clan_id=? WHERE user_id=?", (clan_id, message.from_user.id))
        await db.commit()
    await message.answer(f"🏰 Клан **{name}** создан!")

@router.callback_query(F.data == "loans_info")
async def loans_info(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, lender_id, amount, percent FROM loans WHERE borrower_id=? AND status='active'", (callback.from_user.id,)) as cur:
            loans = await cur.fetchall()
    text = "📜 **Твои кредиты:**\n\n" if loans else "📜 У тебя нет активных кредитов.\n\nВзять кредит в банке: /loan Сумма"
    for l in loans:
        text += f"Кредит #{l[0]}: {l[2]} монет под {l[3]}%\n"
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(F.text.startswith("/loan "))
async def take_loan(message: Message):
    try: amount = int(message.text.split()[1])
    except: return
    if amount > 10000: return await message.answer("Максимум 10000 монет.")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amount, message.from_user.id))
        await db.execute("INSERT INTO loans (lender_id, borrower_id, amount, percent) VALUES (0, ?, ?, 10)", (message.from_user.id, amount))
        await db.commit()
    await message.answer(f"💰 Взят кредит: {amount} монет под 10%")

@router.callback_query(F.data == "gift_info")
async def gift_info(callback: CallbackQuery):
    await callback.message.edit_text("🎁 Чтобы подарить монеты, используй кнопку 💸 Перевод в главном меню.")
    await callback.answer()
