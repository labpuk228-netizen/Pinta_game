import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import section_menu

router = Router()

@router.message(F.text == "📈 Биржа")
async def market_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Криптовалюта", callback_data="mkt_crypto")],
        [InlineKeyboardButton(text="📊 Акции", callback_data="mkt_stocks")]
    ])
    await message.answer("📈 **Фондовая биржа**\n\nВыбери рынок:", parse_mode="Markdown", reply_markup=kb)
    await message.answer("Навигация:", reply_markup=section_menu())

@router.callback_query(F.data == "mkt_crypto")
async def show_crypto(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, name, price FROM crypto_assets") as cur:
            assets = await cur.fetchall()
    
    text = "🪙 **Криптовалюты** (курс обновляется каждые 5 мин):\n\n"
    kb = []
    for a in assets:
        text += f"**{a[1]}** ({a[0]}): {a[2]:.2f} монет\n"
        kb.append([
            InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"mkt_buy_{a[0]}"),
            InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"mkt_sell_{a[0]}")
        ])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_back")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "mkt_stocks")
async def show_stocks(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, name, price FROM stock_assets") as cur:
            assets = await cur.fetchall()
    
    text = "📊 **Акции компаний** (курс обновляется каждые 5 мин):\n\n"
    kb = []
    for a in assets:
        text += f"**{a[1]}** ({a[0]}): {a[2]:.2f} монет\n"
        kb.append([
            InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"mkt_buy_{a[0]}"),
            InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"mkt_sell_{a[0]}")
        ])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_back")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "mkt_back")
async def mkt_back(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Криптовалюта", callback_data="mkt_crypto")],
        [InlineKeyboardButton(text="📊 Акции", callback_data="mkt_stocks")]
    ])
    await callback.message.edit_text("📈 **Фондовая биржа**\n\nВыбери рынок:", parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

# Покупка/продажа (упрощенно: покупаем/продаем 1 единицу)
@router.callback_query(F.data.startswith("mkt_buy_") | F.data.startswith("mkt_sell_"))
async def trade_asset(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1] # buy или sell
    symbol = parts[2]
    
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Ищем в крипте
        async with db.execute("SELECT price FROM crypto_assets WHERE symbol=?", (symbol,)) as cur:
            asset = await cur.fetchone()
            is_crypto = True
            db_col = f"crypto_{symbol.lower()}"
        
        # Если нет, ищем в акциях
        if not asset:
            async with db.execute("SELECT price FROM stock_assets WHERE symbol=?", (symbol,)) as cur:
                asset = await cur.fetchone()
                is_crypto = False
                db_col = "stock_pinta" # Упрощение для демо
        
        if not asset:
            await callback.answer("Актив не найден.", show_alert=True)
            return
            
        price = asset[0]
        
        if action == "buy":
            if player[3] < price:
                await callback.answer("Недостаточно средств!", show_alert=True)
                return
            await db.execute(f"UPDATE players SET balance = balance - ?, {db_col} = {db_col} + 1 WHERE user_id=?", (price, callback.from_user.id))
        else: # sell
            # Проверяем, есть ли у игрока этот актив
            idx = 13 if symbol == "BTC" else 14 if symbol == "ETH" else 15
            if player[idx] < 1:
                await callback.answer("У тебя нет этого актива!", show_alert=True)
                return
            await db.execute(f"UPDATE players SET balance = balance + ?, {db_col} = {db_col} - 1 WHERE user_id=?", (price, callback.from_user.id))
            
        await db.commit()
    
    await callback.answer(f"Сделка совершена: {action} {symbol} за {price:.2f} монет!", show_alert=True)

@router.message(F.text == "💼 Портфель")
async def portfolio(message: Message):
    p = await get_player(message.from_user.id)
    await message.answer(
        f"💼 **Твой портфель:**\n\n"
        f"🪙 BTC: {p[13]:.4f}\n"
        f"🪙 ETH: {p[14]:.4f}\n"
        f"📊 PINTA: {p[15]:.4f}\n",
        parse_mode="Markdown",
        reply_markup=section_menu()
)
