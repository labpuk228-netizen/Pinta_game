import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_player, DB_PATH
from keyboards import market_menu
from states import TradeState, OrderState

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
        kb.append([InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"ask_buy_{a[0]}"), InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"ask_sell_{a[0]}")])
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
        kb.append([InlineKeyboardButton(text=f"Купить {a[0]}", callback_data=f"ask_buy_{a[0]}"), InlineKeyboardButton(text=f"Продать {a[0]}", callback_data=f"ask_sell_{a[0]}")])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("ask_buy_") | F.data.startswith("ask_sell_"))
async def ask_amount(callback: CallbackQuery, state: FSMContext):
    action, symbol = callback.data.split("_")[1], callback.data.split("_")[2]
    await state.update_data(action=action, symbol=symbol)
    await state.set_state(TradeState.waiting_amount)
    text = f"Введи **сумму в монетах**, которую хочешь потратить на покупку {symbol}:" if action == "buy" else f"Введи **количество {symbol}**, которое хочешь продать (например, `0.5`):"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(TradeState.waiting_amount)
async def process_trade(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(',', '.'))
        if val <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число больше нуля.")
        return
    data = await state.get_data()
    action, symbol = data['action'], data['symbol']
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT price FROM crypto_assets WHERE symbol=?", (symbol,)) as cur:
            res = await cur.fetchone()
            if not res:
                async with db.execute("SELECT price FROM stock_assets WHERE symbol=?", (symbol,)) as cur2:
                    res = await cur2.fetchone()
        price = res[0]
        if action == 'buy':
            cost = val
            amount = cost / price
            if player[3] < cost:
                await message.answer(f"❌ Недостаточно монет! У тебя только {player[3]} 💰.")
                await state.clear()
                return
            await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (cost, message.from_user.id))
            await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, ?, ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (message.from_user.id, symbol, amount, amount))
        else:
            amount = val
            async with db.execute("SELECT amount FROM market_portfolio WHERE user_id=? AND symbol=?", (message.from_user.id, symbol)) as cur:
                res = await cur.fetchone()
                have = res[0] if res else 0
            if have < amount:
                await message.answer(f"❌ У тебя только {have:.6f} {symbol}.")
                await state.clear()
                return
            profit = amount * price
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (profit, message.from_user.id))
            await db.execute("UPDATE market_portfolio SET amount = amount - ? WHERE user_id=? AND symbol=?", (amount, message.from_user.id, symbol))
        await db.commit()
    if action == 'buy': text = f"✅ Куплено {amount:.6f} {symbol} на сумму {cost:.2f} 💰."
    else: text = f"✅ Продано {amount:.6f} {symbol} за {profit:.2f} 💰."
    await message.answer(text, parse_mode="Markdown")
    await state.clear()

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
            text += f"▪️ {p[0]}: {p[1]:.6f} шт. (Стоимость: {val:.2f} 💰)\n"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text.contains("ордера"))
async def my_orders_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🪙 Крипта", callback_data="ord_asset_crypto")],[InlineKeyboardButton(text="📊 Акции", callback_data="ord_asset_stock")]])
    await message.answer("📜 **Мои ордера**\n\nВыбери тип актива, чтобы выставить лимитный ордер:", parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data.startswith("ord_asset_"))
async def order_choose_asset(callback: CallbackQuery):
    table = "crypto_assets" if "crypto" in callback.data else "stock_assets"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT symbol FROM {table}") as cur:
            assets = await cur.fetchall()
    kb = [[InlineKeyboardButton(text=a[0], callback_data=f"ord_action_{a[0]}")] for a in assets]
    await callback.message.edit_text("Выбери актив:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("ord_action_"))
async def order_choose_action(callback: CallbackQuery):
    symbol = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Купить", callback_data=f"ord_start_buy_{symbol}")],[InlineKeyboardButton(text="Продать", callback_data=f"ord_start_sell_{symbol}")]])
    await callback.message.edit_text(f"Актив {symbol}. Выбери действие:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("ord_start_"))
async def order_start(callback: CallbackQuery, state: FSMContext):
    action, symbol = callback.data.split("_")[2], callback.data.split("_")[3]
    await state.update_data(action=action, symbol=symbol)
    await state.set_state(OrderState.waiting_amount)
    await callback.message.edit_text(f"Введи количество **{symbol}** для ордера (например, `1.5`):", parse_mode="Markdown")
    await callback.answer()

@router.message(OrderState.waiting_amount)
async def order_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число.")
        return
    await state.update_data(amount=amount)
    await state.set_state(OrderState.waiting_price)
    await message.answer("Теперь введи **желаемую цену** за 1 единицу:")

@router.message(OrderState.waiting_price)
async def order_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректную цену.")
        return
    data = await state.get_data()
    action, symbol, amount = data['action'], data['symbol'], data['amount']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO market_orders (user_id, action, symbol, amount, target_price) VALUES (?, ?, ?, ?, ?)", (message.from_user.id, action, symbol, amount, price))
        await db.commit()
    await message.answer(f"✅ Лимитный ордер создан!\n{'Купить' if action == 'buy' else 'Продать'} {amount:.6f} {symbol}, когда цена достигнет {price:.2f} 💰.", parse_mode="Markdown")
    await state.clear()
