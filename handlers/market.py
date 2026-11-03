import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import market_menu

router = Router()

@router.message(F.text.contains("Биржа"))
async def market_hub(message: Message):
    await message.answer("📈 **Фондовая биржа**\n\nВыбери рынок или посмотри свой портфель.", reply_markup=market_menu())

@router.message(F.text.contains("Крипта"))
async def show_crypto(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, name, price FROM crypto_assets") as cur:
            assets = await cur.fetchall()
    
    text = "🪙 **Криптовалюты** (курс обновляется каждые 5 мин):\n\n"
    kb = []
    for a in assets:
        text += f"**{a[1]}** ({a[0]}): {a[2]:.2f} монет\n"
        kb.append([
            InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"buycrypto_{a[0]}"),
            InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"sellcrypto_{a[0]}")
        ])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.contains("Акции"))
async def show_stocks(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, name, price FROM stock_assets") as cur:
            assets = await cur.fetchall()
    
    text = "📊 **Акции компаний:**\n\n"
    kb = []
    for a in assets:
        text += f"**{a[1]}** ({a[0]}): {a[2]:.2f} монет\n"
        kb.append([
            InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"buystock_{a[0]}"),
            InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"sellstock_{a[0]}")
        ])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.contains("Портфель"))
async def portfolio(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, amount FROM market_portfolio WHERE user_id=? AND amount > 0", (message.from_user.id,)) as cur:
            portfolio = await cur.fetchall()
            
    if not portfolio:
        await message.answer("💼 Твой портфель пуст.")
        return
        
    text = "💼 **Твой портфель:**\n\n"
    for p in portfolio:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT price FROM crypto_assets WHERE symbol=?", (p[0],)) as cur:
                price = await cur.fetchone()
                if not price:
                    async with db.execute("SELECT price FROM stock_assets WHERE symbol=?", (p[0],)) as cur2:
                        price = await cur2.fetchone()
            val = price[0] * p[1] if price else 0
            text += f"▪️ {p[0]}: {p[1]:.4f} шт. (Стоимость: {val:.2f} 💰)\n"
            
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text.contains("ордера"))
async def my_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, action, symbol, amount, target_price FROM market_orders WHERE user_id=? AND status='active'", (message.from_user.id,)) as cur:
            orders = await cur.fetchall()
            
    if not orders:
        await message.answer("📜 **Мои ордера**\n\nУ тебя пока нет активных лимитных заявок.\n\n*Чтобы создать ордер, зайди в раздел Крипта или Акции.*")
        return
        
    text = "📜 **Твои активные ордера:**\n\n"
    for o in orders:
        action_text = "Купить" if o[1] == "buy" else "Продать"
        text += f"ID: {o[0]} | {action_text} {o[3]} {o[2]}\nЦена срабатывания: {o[4]:.2f} 💰\n\n"
        
    text += "Чтобы отменить ордер, используй кнопки ниже."
    await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("buycrypto_") | F.data.startswith("buystock_"))
async def buy_asset(callback: CallbackQuery):
    is_crypto = callback.data.startswith("buycrypto_")
    symbol = callback.data.split("_")[1]
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        table = "crypto_assets" if is_crypto else "stock_assets"
        async with db.execute(f"SELECT price FROM {table} WHERE symbol=?", (symbol,)) as cur:
            price = (await cur.fetchone())[0]
            
        if player[3] < price:
            await callback.answer("Недостаточно монет!", show_alert=True)
            return
            
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (price, callback.from_user.id))
        await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, ?, 1) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + 1", (callback.from_user.id, symbol))
        await db.commit()
    
    await callback.answer(f"✅ Куплено 1 {symbol} за {price:.2f} монет!", show_alert=True)

@router.callback_query(F.data.startswith("sellcrypto_") | F.data.startswith("sellstock_"))
async def sell_asset(callback: CallbackQuery):
    is_crypto = callback.data.startswith("sellcrypto_")
    symbol = callback.data.split("_")[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT amount FROM market_portfolio WHERE user_id=? AND symbol=?", (callback.from_user.id, symbol)) as cur:
            amount = (await cur.fetchone())[0]
            
        if amount < 1:
            await callback.answer("У тебя нет этого актива!", show_alert=True)
            return
            
        table = "crypto_assets" if is_crypto else "stock_assets"
        async with db.execute(f"SELECT price FROM {table} WHERE symbol=?", (symbol,)) as cur:
            price = (await cur.fetchone())[0]
            
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (price, callback.from_user.id))
        await db.execute("UPDATE market_portfolio SET amount = amount - 1 WHERE user_id=? AND symbol=?", (callback.from_user.id, symbol))
        await db.commit()
    
    await callback.answer(f"✅ Продано 1 {symbol} за {price:.2f} монет!", show_alert=True)
