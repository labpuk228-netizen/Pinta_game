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
    sql = "SELECT SUM(sp.hashrate * rg.amount) FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, (message.from_user.id,)) as cur:
            th = (await cur.fetchone())[0] or 0
    b, e, d = player[19], player[20], player[23]
    c = player[22] if len(player) > 22 and player[22] else "BTC"
    c_name = {"BTC": "Bitcoin", "ETH": "Ethereum", "DOGE": "Doge"}.get(c, c)
    await message.answer(f"⛏️ **Майнинг-центр**\n\n📈 Хешрейт: {th:.4f}\n🪙 BTC: {b:.6f}\n🪙 ETH: {e:.6f}\n🪙 DOGE: {d:.4f}\n\n⚙️ **Майнишь:** {c_name}", parse_mode="Markdown", reply_markup=mining_menu())

@router.message(F.text.contains("Вывести в портфель"))
async def withdraw_crypto(message: Message):
    p = await get_player(message.from_user.id)
    b, e, d = p[19], p[20], p[23]
    if b == 0 and e == 0 and d == 0: return await message.answer("❌ Нет крипты для вывода.")
    async with aiosqlite.connect(DB_PATH) as db:
        if b > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'BTC', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (message.from_user.id, b, b))
        if e > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'ETH', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (message.from_user.id, e, e))
        if d > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'DOGE', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (message.from_user.id, d, d))
        await db.execute("UPDATE players SET crypto_btc = 0, crypto_eth = 0, crypto_doge = 0 WHERE user_id=?", (message.from_user.id,))
        await db.commit()
    await message.answer(f"✅ Выведено: BTC {b:.6f}, ETH {e:.6f}, DOGE {d:.4f}")

@router.message(F.text.contains("Продать детали"))
async def sell_parts(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sp.id, sp.name, i.amount, i.cond, sp.price FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=?", (message.from_user.id,)) as cur:
            items = await cur.fetchall()
    if not items: return await message.answer("📦 Инвентарь пуст.")
    text, kb = "💸 **Продажа деталей**\n\n", []
    for i in items:
        price = int(i[4] * 0.5 * (i[3] / 100.0))
        text += f"▪️ **{i[1]}** (x{i[2]})\nСостояние: {i[3]:.1f}% | Цена: {price} 💰\n\n"
        kb.append([InlineKeyboardButton(text=f"Продать {i[1]} (+{price}💰)", callback_data=f"sellp_{i[0]}")])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("sellp_"))
async def sell_p(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT i.amount, i.cond, sp.price, sp.name FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=? AND i.part_id=?", (callback.from_user.id, pid)) as cur:
            row = await cur.fetchone()
        if not row or row[0] <= 0: return await callback.answer("Нет детали.", show_alert=True)
        price = int(row[2] * 0.5 * (row[1] / 100.0))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (callback.from_user.id, pid))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (price, callback.from_user.id))
        await db.commit()
    await callback.answer(f"✅ Продано {row[3]} за {price}!", show_alert=True)
    try: await callback.message.delete()
    except: pass

@router.message(F.text.contains("Сменить монету"))
async def change_coin(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Bitcoin (BTC)", callback_data="coin_BTC")],[InlineKeyboardButton(text="Ethereum (ETH)", callback_data="coin_ETH")],[InlineKeyboardButton(text="Doge (DOGE)", callback_data="coin_DOGE")]])
    await message.answer("Выбери монету:", reply_markup=kb)

@router.callback_query(F.data.startswith("coin_"))
async def set_coin(callback: CallbackQuery):
    coin = callback.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET mining_coin=? WHERE user_id=?", (coin, callback.from_user.id))
        await db.commit()
    await callback.message.edit_text(f"✅ Теперь майнишь {coin}")
    await callback.answer()

@router.message(F.text.contains("Магазин деталей"))
async def shop_menu(message: Message):
    if (await is_in_prison(message.from_user.id))[0]: return await message.answer("⛓ Ты в тюрьме!")
    types = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 БП", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    kb = [[InlineKeyboardButton(text=n, callback_data=f"shopcat_{t}")] for t, n in types.items()]
    await message.answer("🛒 **Магазин**:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("shopcat_"))
async def shop_cat(callback: CallbackQuery):
    cat = callback.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, price, hashrate, wattage, slots FROM mining_shop WHERE part_type=?", (cat,)) as cur:
            parts = await cur.fetchall()
    text, kb = f"📦 **Товары:**\n\n", []
    for p in parts:
        stats = []
        if p[3] > 0: stats.append(f"Хеш: +{p[3]}")
        if p[4] > 0: stats.append(f"Ватт: {p[4]}")
        if p[5] > 0: stats.append(f"Слотов: {p[5]}")
        text += f"**{p[1]}**\nЦена: {p[2]} 💰 | {', '.join(stats)}\n\n"
        kb.append([InlineKeyboardButton(text=f"Купить за {p[2]}", callback_data=f"buyp_{p[0]}")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shopback")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "shopback")
async def shop_back(callback: CallbackQuery):
    types = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 БП", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    kb = [[InlineKeyboardButton(text=n, callback_data=f"shopcat_{t}")] for t, n in types.items()]
    await callback.message.edit_text("🛒 **Магазин**:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("buyp_"))
async def buy_p(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    p = await get_player(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name, price FROM mining_shop WHERE id=?", (pid,)) as cur: part = await cur.fetchone()
        if p[3] < part[1]: return await callback.answer("Мало монет!", show_alert=True)
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (part[1], callback.from_user.id))
        await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, 1, 100.0) ON CONFLICT(user_id, part_id) DO UPDATE SET amount = amount + 1", (callback.from_user.id, pid))
        await db.commit()
    await callback.answer(f"✅ Куплено: {part[0]}", show_alert=True)
    async def _render_rigs(target):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name FROM mining_rigs WHERE user_id=?", (target.from_user.id,)) as cur: rigs = await cur.fetchall()
    text, kb = "🖥 **Твои фермы:**\n\n", []
    if not rigs: text += "Нет ферм. Купи корпус!"
    else:
        for r in rigs: kb.append([InlineKeyboardButton(text=f"🖥 {r[1]}", callback_data=f"rig_{r[0]}")])
    kb.append([InlineKeyboardButton(text="➕ Создать ферму", callback_data="create_rig")])
    if isinstance(target, CallbackQuery): await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.contains("Мои фермы"))
async def my_rigs(message: Message):
    if (await is_in_prison(message.from_user.id))[0]: return await message.answer("⛓ Ты в тюрьме!")
    await _render_rigs(message)

@router.callback_query(F.data == "back_rigs")
async def back_rigs(callback: CallbackQuery):
    await _render_rigs(callback)
    await callback.answer()

@router.callback_query(F.data == "create_rig")
async def create_rig(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT i.part_id, s.name FROM mining_inventory i JOIN mining_shop s ON i.part_id = s.id WHERE i.user_id=? AND s.part_type='case'", (callback.from_user.id,)) as cur: cases = await cur.fetchall()
    if not cases: return await callback.answer("Нет корпусов!", show_alert=True)
    kb = [[InlineKeyboardButton(text=f"Создать: {c[1]}", callback_data=f"docrt_{c[0]}")] for c in cases]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_rigs")])
    await callback.message.edit_text("Выбери корпус:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("docrt_"))
async def do_crt(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM mining_shop WHERE id=?", (pid,)) as cur: name = (await cur.fetchone())[0]
        await db.execute("INSERT INTO mining_rigs (user_id, name) VALUES (?, ?)", (callback.from_user.id, name))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (callback.from_user.id, pid))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.commit()
    await callback.answer("✅ Ферма создана!", show_alert=True)
    await _render_rigs(callback)

async def _render_rig(target, rid):
    sql = "SELECT r.name, p_mb.name, p_mb.slots, p_psu.name, p_psu.wattage, p_cpu.name, p_cpu.hashrate FROM mining_rigs r LEFT JOIN mining_shop p_mb ON r.mb_id = p_mb.id LEFT JOIN mining_shop p_psu ON r.psu_id = p_psu.id LEFT JOIN mining_shop p_cpu ON r.cpu_id = p_cpu.id WHERE r.id=?"
    gsql = "SELECT SUM(sp.wattage * rg.amount), SUM(sp.hashrate * rg.amount), SUM(rg.amount) FROM mining_rig_gpus rg JOIN mining_shop sp ON rg.part_id = sp.id WHERE rg.rig_id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, (rid,)) as cur: rig = await cur.fetchone()
        async with db.execute(gsql, (rid,)) as cur: gpu = await cur.fetchone()
    slots, max_w, cpu_h = (rig[2] or 0), (rig[4] or 0), (rig[6] or 0)
    gpu_c, tw, th = (gpu[2] or 0), (gpu[0] or 0), cpu_h + (gpu[1] or 0)
    text = f"🖥 **{rig[0]}**\n\n🔲 Мать: {rig[1] or '❌'} (Слотов: {slots})\n🔌 БП: {rig[3] or '❌'} (Лимит: {max_w}W)\n🧠 Проц: {rig[5] or '❌'}\n🎮 Карт: {gpu_c}/{slots}\n\n⚡ Потр: {tw}/{max_w}W\n📈 Хеш: {th:.4f}\n"
    if tw > max_w and max_w > 0: text += "\n⚠️ **МАЛО МОЩНОСТИ БП!**"
    kb = [[InlineKeyboardButton(text="Установить", callback_data=f"imenu_{rid}")],[InlineKeyboardButton(text="📊 Состояние", callback_data=f"cond_{rid}")],[InlineKeyboardButton(text="🗑 Снять", callback_data=f"rmenu_{rid}")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_rigs")]]
    if isinstance(target, CallbackQuery): await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("rig_"))
async def rig_cfg(callback: CallbackQuery):
    try: await _render_rig(callback, int(callback.data.split("_")[1]))
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("cond_"))
async def show_cond(callback: CallbackQuery):
    try:
        rid = int(callback.data.split("_")[1])
        sql = "SELECT p_mb.name, r.mb_cond, p_psu.name, r.psu_cond, p_cpu.name, r.cpu_cond FROM mining_rigs r LEFT JOIN mining_shop p_mb ON r.mb_id = p_mb.id LEFT JOIN mining_shop p_psu ON r.psu_id = p_psu.id LEFT JOIN mining_shop p_cpu ON r.cpu_id = p_cpu.id WHERE r.id=?"
        gsql = "SELECT sp.name, rg.cond, rg.amount FROM mining_rig_gpus rg JOIN mining_shop sp ON rg.part_id = sp.id WHERE rg.rig_id=?"
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(sql, (rid,)) as cur: rig = await cur.fetchone()
            async with db.execute(gsql, (rid,)) as cur: gpus = await cur.fetchall()
        text = f"📊 **Состояние:**\n\n"
        if rig[0]: text += f"🔲 {rig[0]}: {rig[1]:.1f}%\n"
        if rig[2]: text += f"🔌 {rig[2]}: {rig[3]:.1f}%\n"
        if rig[4]: text += f"🧠 {rig[4]}: {rig[5]:.1f}%\n"
        for g in gpus: text += f"🎮 {g[0]} x{g[2]}: {g[1]:.1f}%\n"
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")]]))
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("rmenu_"))
async def rmenu(callback: CallbackQuery):
    try:
        rid = int(callback.data.split("_")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT mb_id, psu_id, cpu_id FROM mining_rigs WHERE id=?", (rid,)) as cur: rig = await cur.fetchone()
            async with db.execute("SELECT part_id, amount FROM mining_rig_gpus WHERE rig_id=?", (rid,)) as cur: gpus = await cur.fetchall()
        kb = []
        if rig[0]: kb.append([InlineKeyboardButton(text="Снять Мать", callback_data=f"rmp_{rid}_mb")])
        if rig[1]: kb.append([InlineKeyboardButton(text="Снять БП", callback_data=f"rmp_{rid}_psu")])
        if rig[2]: kb.append([InlineKeyboardButton(text="Снять Проц", callback_data=f"rmp_{rid}_cpu")])
        for g in gpus: kb.append([InlineKeyboardButton(text=f"Снять Видюху (x{g[1]})", callback_data=f"rmp_{rid}_gpu_{g[0]}")])
        if not kb: return await callback.message.edit_text("Пусто.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")]]))
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")])
        await callback.message.edit_text("Что снять?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("rmp_"))
async def rmp(callback: CallbackQuery):
    try:
        p = callback.data.split("_")
        rid, pt = int(p[1]), p[2]
        async with aiosqlite.connect(DB_PATH) as db:
            if pt in ("mb", "psu", "cpu"):
                sql = f"SELECT {pt}_id, {pt}_cond FROM mining_rigs WHERE id=?"
                async with db.execute(sql, (rid,)) as cur: row = await cur.fetchone()
                pid, cnd = (row[0] if row else 0), (row[1] if row else 100.0)
                if pid:
                    await db.execute(f"UPDATE mining_rigs SET {pt}_id=0, {pt}_cond=100.0 WHERE id=?", (rid,))
                    async with db.execute("SELECT amount, cond FROM mining_inventory WHERE user_id=? AND part_id=?", (callback.from_user.id, pid)) as cur: inv = await cur.fetchone()
                    if inv:
                        na, ac = inv[0] + 1, (inv[0] * inv[1] + cnd) / (inv[0] + 1)
                        await db.execute("UPDATE mining_inventory SET amount=?, cond=? WHERE user_id=? AND part_id=?", (na, ac, callback.from_user.id, pid))
                    else: await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, 1, ?)", (callback.from_user.id, pid, cnd))
            elif pt == "gpu":
                pid = int(p[3])
                async with db.execute("SELECT amount, cond FROM mining_rig_gpus WHERE rig_id=? AND part_id=?", (rid, pid)) as cur: row = await cur.fetchone()
                amt, cnd = (row[0] if row else 0), (row[1] if row else 100.0)
                if amt > 0:
                    await db.execute("DELETE FROM mining_rig_gpus WHERE rig_id=? AND part_id=?", (rid, pid))
                    async with db.execute("SELECT amount, cond FROM mining_inventory WHERE user_id=? AND part_id=?", (callback.from_user.id, pid)) as cur: inv = await cur.fetchone()
                    if inv:
                        na, ac = inv[0] + amt, (inv[0] * inv[1] + amt * cnd) / (inv[0] + amt)
                        await db.execute("UPDATE mining_inventory SET amount=?, cond=? WHERE user_id=? AND part_id=?", (na, ac, callback.from_user.id, pid))
                    else: await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, ?, ?)", (callback.from_user.id, pid, amt, cnd))
            await db.commit()
        await callback.message.answer("✅ Снято (с износом)!")
        await _render_rig(callback, rid)
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("imenu_"))
async def imenu(callback: CallbackQuery):
    try:
        rid = int(callback.data.split("_")[1])
        sql = "SELECT sp.id, sp.name, sp.part_type, i.amount, i.cond FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=? AND sp.part_type != 'case'"
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(sql, (callback.from_user.id,)) as cur: items = await cur.fetchall()
        if not items: return await callback.answer("Нет деталей!", show_alert=True)
        kb = [[InlineKeyboardButton(text=f"[{i[2].upper()}] {i[1]} (x{i[3]}, {i[4]:.0f}%)", callback_data=f"dinst_{rid}_{i[0]}")] for i in items]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")])
        await callback.message.edit_text("Выбери деталь:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("dinst_"))
async def dinst(callback: CallbackQuery):
    try:
        _, _, rid, pid = callback.data.split("_")
        rid, pid = int(rid), int(pid)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT part_type, name FROM mining_shop WHERE id=?", (pid,)) as cur: pt, nm = await cur.fetchone()
            async with db.execute("SELECT cond FROM mining_inventory WHERE user_id=? AND part_id=?", (callback.from_user.id, pid)) as cur: cnd = (await cur.fetchone())[0]
            if pt == 'gpu': await db.execute("INSERT INTO mining_rig_gpus (rig_id, part_id, amount, cond) VALUES (?, ?, 1, ?) ON CONFLICT(rig_id, part_id) DO UPDATE SET amount = amount + 1", (rid, pid, cnd))
            elif pt in ('mb', 'psu', 'cpu'): await db.execute(f"UPDATE mining_rigs SET {pt}_id=?, {pt}_cond=? WHERE id=?", (pid, cnd, rid))
            await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (callback.from_user.id, pid))
            await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
            await db.commit()
        await callback.message.answer(f"✅ {nm} установлен (Износ: {cnd:.0f}%)!")
        await _render_rig(callback, rid)
    except Exception as e: await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()
