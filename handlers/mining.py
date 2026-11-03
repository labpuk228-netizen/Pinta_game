import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH, is_in_prison
from keyboards import mining_menu

router = Router()

@router.message(F.text.contains("Майнинг"))
async def mining_hub(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Майнинг недоступен. Осталось: {mins} мин.")
        return
        
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT SUM(sp.hashrate * rg.amount) FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id=?", (message.from_user.id,)) as cur:
            total_hash = (await cur.fetchone())[0] or 0
            
    btc = player[19] if len(player) > 19 and player[19] else 0.0
    eth = player[20] if len(player) > 20 and player[20] else 0.0
    doge = player[23] if len(player) > 23 and player[23] else 0.0
    coin = player[22] if len(player) > 22 and player[22] else "BTC"
    coin_name = {"BTC": "Bitcoin", "ETH": "Ethereum", "DOGE": "Doge"}.get(coin, coin)
    
    await message.answer(
        f"⛏️ **Майнинг-центр**\n\n"
        f"📈 Твой общий хешрейт: {total_hash:.4f}\n"
        f"🪙 Добыто BTC: {btc:.6f}\n"
        f"🪙 Добыто ETH: {eth:.6f}\n"
        f"🪙 Добыто DOGE: {doge:.4f}\n\n"
        f"⚙️ **Сейчас майнишь:** {coin_name}",
        parse_mode="Markdown", reply_markup=mining_menu()
    )

@router.message(F.text.contains("Сменить монету"))
async def change_coin_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Bitcoin (BTC)", callback_data="setcoin_BTC")],
        [InlineKeyboardButton(text="Ethereum (ETH)", callback_data="setcoin_ETH")],
        [InlineKeyboardButton(text="Doge (DOGE)", callback_data="setcoin_DOGE")]
    ])
    await message.answer("Выбери монету для майнинга:", reply_markup=kb)

@router.callback_query(F.data.startswith("setcoin_"))
async def set_coin(callback: CallbackQuery):
    coin = callback.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET mining_coin=? WHERE user_id=?", (coin, callback.from_user.id))
        await db.commit()
    await callback.message.edit_text(f"✅ Теперь ты майнишь {coin}")

@router.message(F.text.contains("Магазин деталей"))
async def shop_menu(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    types = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 Блоки питания", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    kb = [[InlineKeyboardButton(text=name, callback_data=f"shopcat_{t}")] for t, name in types.items()]
    await message.answer("🛒 **Магазин комплектующих**\nВыбери категорию:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ... (остальной код mining.py оставляем без изменений, он рабочий)
@router.callback_query(F.data.startswith("shopcat_"))
async def shop_category(callback: CallbackQuery):
    cat = callback.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, price, hashrate, wattage, slots FROM mining_shop WHERE part_type=?", (cat,)) as cur:
            parts = await cur.fetchall()
    text = f"📦 **Товары:**\n\n"
    kb = []
    for p in parts:
        stats = []
        if p[3] > 0: stats.append(f"Хешрейт: +{p[3]}")
        if p[4] > 0: stats.append(f"Ватт: {p[4]}")
        if p[5] > 0: stats.append(f"Слотов: {p[5]}")
        text += f"**{p[1]}**\nЦена: {p[2]} 💰 | {', '.join(stats)}\n\n"
        kb.append([InlineKeyboardButton(text=f"Купить за {p[2]}", callback_data=f"buypart_{p[0]}")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shopback")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "shopback")
async def shop_back(callback: CallbackQuery):
    types = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 Блоки питания", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    kb = [[InlineKeyboardButton(text=name, callback_data=f"shopcat_{t}")] for t, name in types.items()]
    await callback.message.edit_text("🛒 **Магазин комплектующих**\nВыбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("buypart_"))
async def buy_part(callback: CallbackQuery):
    part_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name, price FROM mining_shop WHERE id=?", (part_id,)) as cur:
            part = await cur.fetchone()
        if player[3] < part[1]:
            await callback.answer()
            await callback.message.answer("❌ Недостаточно монет!")
            return
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (part[1], callback.from_user.id))
        await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount) VALUES (?, ?, 1) ON CONFLICT(user_id, part_id) DO UPDATE SET amount = amount + 1", (callback.from_user.id, part_id))
        await db.commit()
    await callback.answer()
    await callback.message.answer(f"✅ Куплено: {part[0]}")

async def _render_rigs(target):
    user_id = target.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name FROM mining_rigs WHERE user_id=?", (user_id,)) as cur:
            rigs = await cur.fetchall()
    text = "🖥 **Твои фермы:**\n\n"
    kb = []
    if not rigs: text += "У тебя нет ферм. Купи 📦 Корпус в магазине деталей!"
    else:
        for r in rigs: kb.append([InlineKeyboardButton(text=f"🖥 {r[1]}", callback_data=f"rig_{r[0]}")])
    kb.append([InlineKeyboardButton(text="➕ Создать ферму из корпуса", callback_data="create_rig")])
    if isinstance(target, CallbackQuery): await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.contains("Мои фермы"))
async def my_rigs(message: Message):
    in_prison, mins = await is_in_prison(message.from_user.id)
    if in_prison:
        await message.answer(f"⛓ Ты в тюрьме! Осталось: {mins} мин.")
        return
    await _render_rigs(message)

@router.callback_query(F.data == "back_rigs")
async def back_rigs(callback: CallbackQuery):
    await _render_rigs(callback)
    await callback.answer()

@router.callback_query(F.data == "create_rig")
async def create_rig(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT i.part_id, s.name FROM mining_inventory i JOIN mining_shop s ON i.part_id = s.id WHERE i.user_id=? AND s.part_type='case'", (callback.from_user.id,)) as cur:
            cases = await cur.fetchall()
    if not cases:
        await callback.answer()
        await callback.message.answer("❌ У тебя нет купленных корпусов!")
        return
    kb = [[InlineKeyboardButton(text=f"Создать: {c[1]}", callback_data=f"docreate_{c[0]}")] for c in cases]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_rigs")])
    await callback.message.edit_text("Выбери корпус для новой фермы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("docreate_"))
async def do_create_rig(callback: CallbackQuery):
    part_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM mining_shop WHERE id=?", (part_id,)) as cur:
            case_name = (await cur.fetchone())[0]
        await db.execute("INSERT INTO mining_rigs (user_id, name) VALUES (?, ?)", (callback.from_user.id, case_name))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (callback.from_user.id, part_id))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.commit()
    await callback.answer()
    await callback.message.answer("✅ Ферма создана!")
    await _render_rigs(callback)

async def _render_rig_config(target, rig_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT r.name, p_mb.name, p_mb.slots, p_psu.name, p_psu.wattage, p_cpu.name, p_cpu.hashrate FROM mining_rigs r LEFT JOIN mining_shop p_mb ON r.mb_id = p_mb.id LEFT JOIN mining_shop p_psu ON r.psu_id = p_psu.id LEFT JOIN mining_shop p_cpu ON r.cpu_id = p_cpu.id WHERE r.id=?", (rig_id,)) as cur:
            rig = await cur.fetchone()
        async with db.execute("SELECT SUM(sp.wattage * rg.amount), SUM(sp.hashrate * rg.amount), SUM(rg.amount) FROM mining_rig_gpus rg JOIN mining_shop sp ON rg.part_id = sp.id WHERE rg.rig_id=?", (rig_id,)) as cur:
            gpu_stats = await cur.fetchone()
    mb_slots = rig[2] if rig[2] else 0
    psu_max_w = rig[4] if rig[4] else 0
    cpu_hash = rig[6] if rig[6] else 0
    gpu_count = gpu_stats[2] if gpu_stats[2] else 0
    total_w = (gpu_stats[0] if gpu_stats[0] else 0)
    total_hash = cpu_hash + (gpu_stats[1] if gpu_stats[1] else 0)
    text = f"🖥 **{rig[0]}**\n\n🔲 Материнка: {rig[1] or '❌ Нет'} (Слотов: {mb_slots})\n🔌 БП: {rig[3] or '❌ Нет'} (Лимит: {psu_max_w}W)\n🧠 Процессор: {rig[5] or '❌ Нет'}\n🎮 Видеокарт: {gpu_count}/{mb_slots}\n\n⚡ Потребление: {total_w}/{psu_max_w}W\n📈 Хешрейт: {total_hash:.4f}\n"
    if total_w > psu_max_w and psu_max_w > 0: text += "\n⚠️ **ВНИМАНИЕ: Не хватает мощности БП!**"
    kb = [[InlineKeyboardButton(text="Установить деталь", callback_data=f"install_menu_{rig_id}")],[InlineKeyboardButton(text="⬅️ К фермам", callback_data="back_rigs")]]
    if isinstance(target, CallbackQuery): await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("rig_"))
async def rig_config(callback: CallbackQuery):
    await _render_rig_config(callback, int(callback.data.split("_")[1]))
    await callback.answer()

@router.callback_query(F.data.startswith("install_menu_"))
async def install_part_menu(callback: CallbackQuery):
    rig_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sp.id, sp.name, sp.part_type, i.amount FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=? AND sp.part_type != 'case'", (callback.from_user.id,)) as cur:
            items = await cur.fetchall()
    if not items:
        await callback.answer()
        await callback.message.answer("❌ У тебя нет деталей в инвентаре!")
        return
    kb = [[InlineKeyboardButton(text=f"[{i[2].upper()}] {i[1]} (x{i[3]})", callback_data=f"do_install_{rig_id}_{i[0]}")] for i in items]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rig_id}")])
    await callback.message.edit_text("Выбери деталь для установки:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("do_install_"))
async def do_install(callback: CallbackQuery):
    _, _, rig_id, part_id = callback.data.split("_")
    rig_id, part_id = int(rig_id), int(part_id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT part_type, name FROM mining_shop WHERE id=?", (part_id,)) as cur:
            part = await cur.fetchone()
        ptype = part[0]
        if ptype == 'gpu':
            await db.execute("INSERT INTO mining_rig_gpus (rig_id, part_id, amount) VALUES (?, ?, 1) ON CONFLICT(rig_id, part_id) DO UPDATE SET amount = amount + 1", (rig_id, part_id))
        elif ptype in ('mb', 'psu', 'cpu'):
            await db.execute(f"UPDATE mining_rigs SET {ptype}_id=? WHERE id=?", (part_id, rig_id))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (callback.from_user.id, part_id))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.commit()
    await callback.answer()
    await callback.message.answer(f"✅ {part[1]} установлен!")
    await _render_rig_config(callback, rig_id)
