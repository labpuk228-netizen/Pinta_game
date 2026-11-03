import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import social_menu # ИСПРАВЛЕНО: импортируем social_menu

router = Router()

@router.message(F.text.contains("Социалка"))
async def social_hub(message: Message):
    # ИСПРАВЛЕНО: используем social_menu
    await message.answer("🤝 **Социальное меню**\n\nВыбери действие снизу.", reply_markup=social_menu())

@router.message(F.text.contains("Кредиты"))
async def loans_menu(message: Message):
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, amount, percent FROM loans WHERE borrower_id=? AND status='active'", (message.from_user.id,)) as cur:
            loans = await cur.fetchall()
            
    text = "🏦 **Банк**\n\n"
    if loans:
        for l in loans:
            text += f"Кредит #{l[0]}: {l[1]} монет под {l[2]}%\n"
    else:
        text += "У тебя нет активных кредитов.\n"
        
    text += "\nНапиши `/loan Сумма`, чтобы взять кредит (макс 5000, ставка 10%)."
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text.startswith("/loan "))
async def take_loan(message: Message):
    try:
        amount = int(message.text.split()[1])
        if amount <= 0 or amount > 5000: raise ValueError
    except:
        await message.answer("❌ Введи сумму от 1 до 5000. Пример: `/loan 1000`", parse_mode="Markdown")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amount, message.from_user.id))
        await db.execute("INSERT INTO loans (lender_id, borrower_id, amount, percent) VALUES (0, ?, ?, 10)", (message.from_user.id, amount))
        await db.commit()
    await message.answer(f"✅ Выдан кредит: {amount} монет под 10%.")

@router.message(F.text.contains("Кланы"))
async def clans_menu(message: Message):
    player = await get_player(message.from_user.id)
    if player[14] == 0: # clan_id
        await message.answer("🏰 Ты не в клане.\n\nНапиши `/create_clan Название`, чтобы создать его (стоит 5000 монет).")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name, bank FROM clans WHERE id=?", (player[14],)) as cur:
                clan = await cur.fetchone()
        await message.answer(f"🏰 Клан: **{clan[0]}**\n💰 Банк: {clan[1]} монет", parse_mode="Markdown")

@router.message(F.text.startswith("/create_clan "))
async def create_clan(message: Message):
    name = message.text.split(" ", 1)[1]
    player = await get_player(message.from_user.id)
    if player[3] < 5000:
        await message.answer("❌ Нужно 5000 монет для создания клана.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 5000 WHERE user_id=?", (message.from_user.id,))
        await db.execute("INSERT INTO clans (name, leader_id) VALUES (?, ?)", (name, message.from_user.id))
        async with db.execute("SELECT last_insert_rowid()") as cur:
            clan_id = (await cur.fetchone())[0]
        await db.execute("UPDATE players SET clan_id=? WHERE user_id=?", (clan_id, message.from_user.id))
        await db.commit()
    await message.answer(f"🏰 Клан **{name}** создан!")
