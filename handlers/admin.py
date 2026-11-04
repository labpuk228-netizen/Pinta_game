import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SECRET_ADMIN_CODE, ADMIN_ID
from database import DB_PATH
from keyboards import main_menu, admin_menu, admin_players_menu, admin_economy_menu, admin_events_menu

router = Router()

class AdminStates(StatesGroup):
    waiting_balance_id = State()
    waiting_balance_amount = State()
    waiting_ban_id = State()
    waiting_broadcast = State()
    waiting_symbol = State()
    waiting_price = State()
    waiting_biz_id = State()
    waiting_biz_price = State()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

@router.message(F.text == SECRET_ADMIN_CODE)
async def admin_entry(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("🛡 **Режим администратора активирован.**", parse_mode="Markdown", reply_markup=main_menu(is_admin=True))

@router.message(F.text == "🛡 Админ-панель")
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("🛠 **Главное меню админа:**", reply_markup=admin_menu())

@router.message(F.text == "⬅️ Назад в меню")
async def back_to_main(message: Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_menu(is_admin=True))

@router.message(F.text == "⬅️ В админку")
async def back_to_admin(message: Message):
    await message.answer("🛠 **Главное меню админа:**", reply_markup=admin_menu())

# --- ИГРОКИ ---
@router.message(F.text == "👥 Игроки")
async def admin_players(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("👥 **Управление игроками:**", reply_markup=admin_players_menu())

@router.message(F.text == "💰 Выдать монеты")
async def admin_give_balance(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_balance_id)
    await message.answer("Введи **ID игрока**, которому нужно начислить монеты:")

@router.message(AdminStates.waiting_balance_id)
async def admin_process_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("ID должен быть числом.")
    await state.update_data(target_id=int(message.text))
    await state.set_state(AdminStates.waiting_balance_amount)
    await message.answer("Введи **сумму** (например, 10000):")

@router.message(AdminStates.waiting_balance_amount)
async def admin_process_amount(message: Message, state: FSMContext):
    try: amount = int(message.text)
    except: return await message.answer("Введи целое число.")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amount, data['target_id']))
        await db.commit()
    await message.answer(f"✅ Игроку {data['target_id']} начислено {amount} монет.", reply_markup=admin_players_menu())
    await state.clear()

@router.message(F.text == "🚫 Забанить")
async def admin_ban(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_ban_id)
    await message.answer("Введи **ID игрока**, которого нужно забанить:")

@router.message(AdminStates.waiting_ban_id)
async def admin_process_ban(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("ID должен быть числом.")
    target_id = int(message.text)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET is_banned=1 WHERE user_id=?", (target_id,))
        await db.commit()
    await message.answer(f"🚫 Игрок {target_id} забанен.", reply_markup=admin_players_menu())
    await state.clear()

# --- БИРЖА ---
@router.message(F.text == "📈 Биржа")
async def admin_market(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_symbol)
    await message.answer("Введи **тикер** (BTC, ETH, DOGE, PINTA или TECH):")

@router.message(AdminStates.waiting_symbol)
async def admin_process_symbol(message: Message, state: FSMContext):
    sym = message.text.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM crypto_assets WHERE symbol=?", (sym,)) as cur:
            is_crypto = await cur.fetchone()
        async with db.execute("SELECT 1 FROM stock_assets WHERE symbol=?", (sym,)) as cur:
            is_stock = await cur.fetchone()
            
    if not is_crypto and not is_stock:
        return await message.answer("Такого тикера нет.")
        
    await state.update_data(symbol=sym, is_crypto=bool(is_crypto))
    await state.set_state(AdminStates.waiting_price)
    await message.answer(f"Введи **новую цену** для {sym}:")

@router.message(AdminStates.waiting_price)
async def admin_process_price(message: Message, state: FSMContext):
    try: price = float(message.text)
    except: return await message.answer("Введи число.")
    data = await state.get_data()
    table = "crypto_assets" if data['is_crypto'] else "stock_assets"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE {table} SET price=? WHERE symbol=?", (price, data['symbol']))
        await db.commit()
    await message.answer(f"✅ Курс {data['symbol']} изменён на {price}.", reply_markup=admin_menu())
    await state.clear()
# --- ЭКОНОМИКА ---
@router.message(F.text == "💰 Экономика")
async def admin_economy(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("💰 **Управление экономикой:**", reply_markup=admin_economy_menu())

@router.message(F.text == "📉 Изменить цены бизнесов")
async def admin_change_biz(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_biz_id)
    await message.answer("Введи **ID бизнеса** (от 1 до 10):")

@router.message(AdminStates.waiting_biz_id)
async def admin_biz_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("ID должен быть числом.")
    await state.update_data(biz_id=int(message.text))
    await state.set_state(AdminStates.waiting_biz_price)
    await message.answer("Введи **новую цену** покупки для этого бизнеса:")

@router.message(AdminStates.waiting_biz_price)
async def admin_biz_price(message: Message, state: FSMContext):
    try: price = int(message.text)
    except: return await message.answer("Введи целое число.")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE businesses SET buy=? WHERE id=?", (price, data['biz_id']))
        await db.commit()
    await message.answer(f"✅ Цена бизнеса ID {data['biz_id']} изменена на {price}.", reply_markup=admin_economy_menu())
    await state.clear()

# --- ИВЕНТЫ ---
@router.message(F.text == "🌍 Ивенты")
async def admin_events(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("🌍 **Глобальные ивенты:**\n(Меняют множитель цен в экономике)", reply_markup=admin_events_menu())

@router.message(F.text == "🚀 Крипто-бум (+50% к ценам)")
async def admin_boom(message: Message):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price = price * 1.5")
        await db.execute("UPDATE stock_assets SET price = price * 1.5")
        await db.commit()
    await message.answer("🚀 Крипто-бум запущен! Все курсы выросли на 50%.", reply_markup=admin_events_menu())

@router.message(F.text == "📉 Кризис (-30% к ценам)")
async def admin_crisis(message: Message):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price = price * 0.7")
        await db.execute("UPDATE stock_assets SET price = price * 0.7")
        await db.commit()
    await message.answer("📉 Кризис запущен! Все курсы упали на 30%.", reply_markup=admin_events_menu())

# --- СИСТЕМА ---
@router.message(F.text == "📢 Рассылка")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer("Введи текст для рассылки всем игрокам:")

@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM players") as cur:
            users = await cur.fetchall()
            
    count = 0
    for u in users:
        try:
            await message.bot.send_message(u[0], f"📢 **Объявление:**\n\n{message.text}")
            count += 1
        except: pass
    await message.answer(f"✅ Сообщение отправлено {count} игрокам.", reply_markup=admin_menu())
    await state.clear()

@router.message(F.text == "📩 Жалобы")
async def admin_tickets(message: Message):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, user_id, message FROM support_tickets WHERE status='open'") as cur:
            tickets = await cur.fetchall()
            
    if not tickets:
        return await message.answer("Нет активных жалоб.", reply_markup=admin_menu())
        
    for t in tickets:
        await message.answer(f"Тикет #{t[0]}\nОт ID: {t[1]}\nТекст: {t[2]}\n\n(Чтобы ответить, используй /reply {t[1]} текст)")
