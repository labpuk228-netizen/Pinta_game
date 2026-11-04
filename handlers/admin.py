import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SECRET_ADMIN_CODE
from database import DB_PATH, get_player
from keyboards import main_menu

router = Router()

class AdminStates(StatesGroup):
    waiting_balance = State()
    waiting_price = State()
    waiting_broadcast = State()
    waiting_reply = State()
    waiting_biz_price = State()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

def adm_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players_0")],
        [InlineKeyboardButton(text="📈 Биржа", callback_data="adm_market")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="adm_econ")],
        [InlineKeyboardButton(text="🌍 Ивенты", callback_data="adm_events")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📩 Жалобы", callback_data="adm_tickets")]
    ])

@router.message(F.text == SECRET_ADMIN_CODE)
async def admin_entry(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("🛡 Режим админа активирован", reply_markup=main_menu(is_admin=True))
    await message.answer("Выбери раздел:", reply_markup=adm_main_kb())

@router.message(F.text == "🛡 Админ-панель")
async def admin_panel_msg(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("🛡 **Админ-панель:**", reply_markup=adm_main_kb())

@router.callback_query(F.data == "adm_main")
async def adm_back(callback: CallbackQuery):
    await callback.message.edit_text("🛡 **Админ-панель:**", reply_markup=adm_main_kb())

@router.callback_query(F.data.startswith("adm_players_"))
async def adm_players_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    page = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, balance FROM players LIMIT 5 OFFSET ?", (page*5,)) as cur:
            users = await cur.fetchall()
        async with db.execute("SELECT COUNT(*) FROM players") as cur:
            total = (await cur.fetchone())[0]
    kb = []
    for u in users:
        kb.append([InlineKeyboardButton(text=f"@{u[1] or 'Игрок'} (ID:{u[0]}) - {u[2]}💰", callback_data=f"adm_user_{u[0]}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_players_{page-1}"))
    if (page+1)*5 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_players_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")])
    await callback.message.edit_text(f"👥 **Игроки** (стр {page+1}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("adm_user_"))
async def adm_user_card(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    player = await get_player(uid)
    if not player: return await callback.answer("Не найден")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data=f"adm_bal_{uid}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="adm_players_0")]
    ])
    await callback.message.edit_text(f"👤 **Игрок** ID:{uid}\n💰 Баланс: {player[3]}", reply_markup=kb)

@router.callback_query(F.data.startswith("adm_bal_"))
async def adm_ask_bal(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(target_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_balance)
    await callback.message.answer("Введи сумму (можно с минусом):")
    await callback.answer()

@router.message(AdminStates.waiting_balance)
async def adm_set_bal(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try: amt = int(message.text)
    except: return await message.answer("Введи число")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amt, data['target_id']))
        await db.commit()
    await message.answer("✅ Баланс обновлен", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_market")
async def adm_market(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT symbol, price FROM crypto_assets UNION ALL SELECT symbol, price FROM stock_assets") as cur:
            assets = await cur.fetchall()
    text = "📈 **Курсы:**\n" + "\n".join([f"🔹 {a[0]}: {a[1]:.2f}" for a in assets])
    kb = [[InlineKeyboardButton(text=f"Изменить {a[0]}", callback_data=f"adm_chp_{a[0]}")] for a in assets]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_chp_"))
async def adm_ask_price(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(symbol=callback.data.split("_")[2])
    await state.set_state(AdminStates.waiting_price)
    await callback.message.answer("Введи новую цену:")
    await callback.answer()

@router.message(AdminStates.waiting_price)
async def adm_set_price(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try: p = float(message.text)
    except: return await message.answer("Введи число")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price=? WHERE symbol=?", (p, data['symbol']))
        await db.execute("UPDATE stock_assets SET price=? WHERE symbol=?", (p, data['symbol']))
        await db.commit()
    await message.answer(f"✅ Цена {data['symbol']} обновлена", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_econ")
async def adm_econ(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏢 Цены бизнесов", callback_data="adm_econ_biz")],[InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]])
    await callback.message.edit_text("💰 **Экономика:**", reply_markup=kb)

@router.callback_query(F.data == "adm_econ_biz")
async def adm_econ_biz(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, buy FROM businesses") as cur:
            bizs = await cur.fetchall()
    kb = [[InlineKeyboardButton(text=f"Изменить {b[1]}", callback_data=f"adm_chb_{b[0]}")] for b in bizs]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_econ")])
    await callback.message.edit_text("Выбери бизнес:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("adm_chb_"))
async def adm_ask_biz_price(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(biz_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_biz_price)
    await callback.message.answer("Введи цену:")
    await callback.answer()

@router.message(AdminStates.waiting_biz_price)
async def adm_set_biz_price(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try: p = int(message.text)
    except: return await message.answer("Введи число")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE businesses SET buy=? WHERE id=?", (p, data['biz_id']))
        await db.commit()
    await message.answer("✅ Цена бизнеса обновлена", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_events")
async def adm_events(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Крипто-бум", callback_data="adm_boom")],[InlineKeyboardButton(text="📉 Кризис", callback_data="adm_crisis")],[InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]])
    await callback.message.edit_text("🌍 **Ивенты:**", reply_markup=kb)

@router.callback_query(F.data == "adm_boom")
async def adm_boom(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price = price * 1.5")
        await db.execute("UPDATE stock_assets SET price = price * 1.5")
        await db.commit()
    await callback.answer("Бум запущен!", show_alert=True)

@router.callback_query(F.data == "adm_crisis")
async def adm_crisis(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE crypto_assets SET price = price * 0.7")
        await db.execute("UPDATE stock_assets SET price = price * 0.7")
        await db.commit()
    await callback.answer("Кризис запущен!", show_alert=True)

@router.callback_query(F.data == "adm_broadcast")
async def adm_bc(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.answer("Введи текст для рассылки:")
    await callback.answer()

@router.message(AdminStates.waiting_broadcast)
async def adm_bc_send(message: Message, state: FSMContext):
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
    await message.answer(f"✅ Отправлено {count} игрокам", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_tickets")
async def adm_tickets(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, user_id, message FROM support_tickets WHERE status='open'") as cur:
            tickets = await cur.fetchall()
    if not tickets:
        return await callback.message.edit_text("Нет жалоб", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]]))
    kb = [[InlineKeyboardButton(text=f"Тикет #{t[0]} от {t[1]}", callback_data=f"adm_rep_{t[0]}_{t[1]}")] for t in tickets]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")])
    await callback.message.edit_text("📩 **Жалобы:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("adm_rep_"))
async def adm_rep(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    _, _, tid, uid = callback.data.split("_")
    await state.update_data(ticket_id=tid, user_id=uid)
    await state.set_state(AdminStates.waiting_reply)
    await callback.message.answer("Введи ответ:")
    await callback.answer()

@router.message(AdminStates.waiting_reply)
async def adm_rep_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    data = await state.get_data()
    try:
        await message.bot.send_message(int(data['user_id']), f"📩 **Ответ:**\n\n{message.text}")
        await message.answer("✅ Отправлено", reply_markup=adm_main_kb())
    except:
        await message.answer("❌ Игрок заблокировал бота", reply_markup=adm_main_kb())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE support_tickets SET status='closed' WHERE id=?", (data['ticket_id'],))
        await db.commit()
    await state.clear()
