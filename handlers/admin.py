import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SECRET_ADMIN_CODE, ADMIN_ID
from database import DB_PATH, get_player
from keyboards import main_menu

router = Router()

class AdminStates(StatesGroup):
    waiting_balance = State()
    waiting_crypto = State()
    waiting_biz = State()
    waiting_prop = State()
    waiting_ban = State()
    waiting_unban = State()
    waiting_price = State()
    waiting_broadcast = State()
    waiting_reply = State()
    waiting_new_admin = State()

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
        [InlineKeyboardButton(text="📩 Жалобы", callback_data="adm_tickets")],
        [InlineKeyboardButton(text="⚙️ Система (Бэкап/Админы)", callback_data="adm_system")]
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

# --- ИГРОКИ ---
@router.callback_query(F.data.startswith("adm_players_"))
async def adm_players_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    page = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, balance, is_banned FROM players LIMIT 5 OFFSET ?", (page*5,)) as cur:
            users = await cur.fetchall()
        async with db.execute("SELECT COUNT(*) FROM players") as cur:
            total = (await cur.fetchone())[0]
            
    kb = []
    for u in users:
        ban_icon = "🚫" if u[3] == 1 else "✅"
        kb.append([InlineKeyboardButton(text=f"{ban_icon} @{u[1] or 'Игрок'} (ID:{u[0]}) - {u[2]}💰", callback_data=f"adm_user_{u[0]}")])
    
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
    
    ban_btn = InlineKeyboardButton(text="✅ Разбанить" if player[18]==1 else "🚫 Забанить", callback_data=f"adm_ban_{uid}")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data=f"adm_bal_{uid}")],
        [InlineKeyboardButton(text="🪙 Выдать крипту", callback_data=f"adm_crypto_{uid}")],
        [InlineKeyboardButton(text="🏢 Выдать бизнес", callback_data=f"adm_givebiz_{uid}")],
        [InlineKeyboardButton(text="🏠 Выдать жилье", callback_data=f"adm_giveprop_{uid}")],
        [ban_btn],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="adm_players_0")]
    ])
    await callback.message.edit_text(f"👤 **Игрок** ID:{uid}\n💰 Баланс: {player[3]}\nБан: {'Да' if player[18] else 'Нет'}", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_bal_"))
async def adm_ask_bal(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(target_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_balance)
    await callback.message.answer("Введи сумму для начисления (можно с минусом):")
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

@router.callback_query(F.data.startswith("adm_crypto_"))
async def adm_ask_crypto(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(target_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_crypto)
    await callback.message.answer("Введи: `BTC 5` (что и сколько выдать):")
    await callback.answer()

@router.message(AdminStates.waiting_crypto)
async def adm_set_crypto(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try:
        sym, amt = message.text.split()
        amt = float(amt)
    except: return await message.answer("Формат: BTC 5")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        if sym.upper() == "BTC": await db.execute("UPDATE players SET crypto_btc = crypto_btc + ? WHERE user_id=?", (amt, data['target_id']))
        elif sym.upper() == "ETH": await db.execute("UPDATE players SET crypto_eth = crypto_eth + ? WHERE user_id=?", (amt, data['target_id']))
        await db.commit()
    await message.answer("✅ Крипта выдана", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data.startswith("adm_givebiz_"))
async def adm_ask_biz(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(target_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_biz)
    await callback.message.answer("Введи ID бизнеса (от 1 до 5):")
    await callback.answer()

@router.message(AdminStates.waiting_biz)
async def adm_set_biz(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try: bid = int(message.text)
    except: return await message.answer("Введи ID")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO player_businesses (user_id, business_id) VALUES (?, ?)", (data['target_id'], bid))
        await db.commit()
    await message.answer("✅ Бизнес выдан", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data.startswith("adm_giveprop_"))
async def adm_ask_prop(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.update_data(target_id=int(callback.data.split("_")[2]))
    await state.set_state(AdminStates.waiting_prop)
    await callback.message.answer("Введи ID жилья (1 - Общага, 2 - Студия, 3 - Дом):")
    await callback.answer()

@router.message(AdminStates.waiting_prop)
async def adm_set_prop(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    try: pid = int(message.text)
    except: return await message.answer("Введи ID")
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET property_id=? WHERE user_id=?", (pid, data['target_id']))
        await db.commit()
    await message.answer("✅ Жилье выдано", reply_markup=adm_main_kb())
    await state.clear()

@router.callback_query(F.data.startswith("adm_ban_"))
async def adm_ban(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_banned FROM players WHERE user_id=?", (uid,)) as cur:
            curr = (await cur.fetchone())[0]
        new_status = 0 if curr == 1 else 1
        await db.execute("UPDATE players SET is_banned=? WHERE user_id=?", (new_status, uid))
        await db.commit()
    await callback.answer(f"Игрок {'разбанен' if new_status==0 else 'забанен'}")
    await callback.message.edit_text(f"👤 Игрок ID:{uid} обновлен.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 К списку", callback_data="adm_players_0")]]))

# --- БИРЖА ---
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
    await message.answer(f"✅ Цена обновлена", reply_markup=adm_main_kb())
    await state.clear()

# --- ЭКОНОМИКА ---
@router.callback_query(F.data == "adm_econ")
async def adm_econ(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Цены бизнесов", callback_data="adm_econ_biz")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]
    ])
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
    await state.set_state(AdminStates.waiting_price)
    await callback.message.answer("Введи цену:")
    await callback.answer()

# --- ИВЕНТЫ ---
@router.callback_query(F.data == "adm_events")
async def adm_events(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Крипто-бум", callback_data="adm_boom")],
        [InlineKeyboardButton(text="📉 Кризис", callback_data="adm_crisis")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]
    ])
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

# --- СИСТЕМА (БЭКАП И АДМИНЫ) ---
@router.callback_query(F.data == "adm_system")
async def adm_system(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Скачать базу данных", callback_data="adm_backup")],
        [InlineKeyboardButton(text="👑 Выдать права админа", callback_data="adm_newadmin")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_main")]
    ])
    await callback.message.edit_text("⚙️ **Система:**", reply_markup=kb)

@router.callback_query(F.data == "adm_backup")
async def adm_backup(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    try:
        file = FSInputFile(DB_PATH)
        await callback.message.answer_document(file, caption="💾 Резервная копия базы данных.")
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data == "adm_newadmin")
async def adm_new_admin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: 
        return await callback.answer("Только владелец может выдавать админку!", show_alert=True)
    await state.set_state(AdminStates.waiting_new_admin)
    await callback.message.answer("Введи ID игрока, которому дать права админа:")
    await callback.answer()

@router.message(AdminStates.waiting_new_admin)
async def adm_set_new_admin(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try: uid = int(message.text)
    except: return await message.answer("Введи ID")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
        await db.execute("UPDATE players SET is_admin=1 WHERE user_id=?", (uid,))
        await db.commit()
    await message.answer(f"✅ Игрок {uid} теперь админ.", reply_markup=adm_main_kb())
    await state.clear()

# --- РАССЫЛКА И ЖАЛОБЫ ---
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
