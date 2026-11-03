import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import SECRET_ADMIN_CODE
from database import DB_PATH

router = Router()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

@router.message(F.text == SECRET_ADMIN_CODE)
async def admin_entry(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players_0")],
        [InlineKeyboardButton(text="💸 Управление курсами", callback_data="adm_rates")],
        [InlineKeyboardButton(text="⚙️ Тест-цикл", callback_data="adm_run_cycle")]
    ])
    await message.answer("🛠 **Админ-панель**\n\nВыбери раздел:", parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data == "adm_stats")
async def admin_stats(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM players") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM players WHERE last_online > datetime('now','-1 day')") as cur:
            online_24 = (await cur.fetchone())[0]
        async with db.execute("SELECT SUM(balance) FROM players") as cur:
            total_money = (await cur.fetchone())[0] or 0
            
    text = (
        f"📊 **Статистика мира**\n\n"
        f"👥 Всего игроков: {total}\n"
        f"🟢 Активны за 24ч: {online_24}\n"
        f"💰 Всего монет в экономике: {total_money}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")]]))
    await callback.answer()

@router.callback_query(F.data.startswith("adm_players_"))
async def admin_players(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    page = int(callback.data.split("_")[2])
    limit = 5
    offset = page * limit
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, balance, last_online FROM players ORDER BY last_online DESC LIMIT ? OFFSET ?", (limit, offset)) as cur:
            players = await cur.fetchall()
        async with db.execute("SELECT COUNT(*) FROM players") as cur:
            total = (await cur.fetchone())[0]
            
    text = f"👥 **Игроки** (стр. {page+1}):\n\n"
    for p in players:
        text += f"ID: `{p[0]}` | @{p[1]} | 💰 {p[2]}\nБыл: {p[3]}\n\n"
    
    kb = []
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_players_{page-1}"))
    if offset + limit < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_players_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")])
    
    await callback.message.edit_text(text[:4000], parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "adm_rates")
async def admin_rates(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, price FROM crypto_assets") as cur:
            crypto = await cur.fetchall()
        async with db.execute("SELECT symbol, price FROM stock_assets") as cur:
            stocks = await cur.fetchall()
            
    text = "💸 **Текущие курсы:**\n\n"
    for c in crypto: text += f"🪙 {c[0]}: {c[1]:.2f}\n"
    for s in stocks: text += f"📊 {s[0]}: {s[1]:.2f}\n"
    
    text += "\nЧтобы изменить курс, отправь команду:\n`/setprice BTC 750`"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")]]))
    await callback.answer()

@router.message(F.text.startswith("/setprice "))
async def set_price(message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        _, symbol, price_str = message.text.split()
        price = float(price_str)
    except:
        await message.answer("Формат: `/setprice BTC 750`", parse_mode="Markdown")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price=? WHERE symbol=?", (price, symbol.upper()))
        await db.execute("UPDATE stock_assets SET price=? WHERE symbol=?", (price, symbol.upper()))
        await db.commit()
    await message.answer(f"✅ Курс {symbol.upper()} изменен на {price}")

@router.callback_query(F.data == "adm_back")
async def admin_back(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players_0")],
        [InlineKeyboardButton(text="💸 Управление курсами", callback_data="adm_rates")],
        [InlineKeyboardButton(text="⚙️ Тест-цикл", callback_data="adm_run_cycle")]
    ])
    await callback.message.edit_text("🛠 **Админ-панель**\n\nВыбери раздел:", parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "adm_run_cycle")
async def adm_run_cycle(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    from tasks.scheduler import process_cycle
    try:
        await process_cycle()
        await callback.answer("✅ Пассивный цикл выполнен (зарплаты, налоги, майнинг)!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
