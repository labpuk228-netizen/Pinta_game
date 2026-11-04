import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH, is_in_prison
from keyboards import mining_menu

router = Router()

@router.message(F.text.contains("Майнинг"))
async def m_hub(m: Message):
    if (await is_in_prison(m.from_user.id))[0]: return await m.answer("⛓ Тюрьма!")
    p = await get_player(m.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT SUM(sp.hashrate * rg.amount) FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id=?", (m.from_user.id,)) as c: th = (await c.fetchone())[0] or 0
    
    b, e, d = p[21], p[22], p[25]
    cn = {"BTC": "Bitcoin", "ETH": "Ethereum", "DOGE": "Doge"}.get(p[24] or "BTC", "BTC")
    
    await m.answer(f"⛏️ **Майнинг**\n📈 Хеш: {th:.4f}\n🪙 BTC: {b:.6f}\n🪙 ETH: {e:.6f}\n🪙 DOGE: {d:.4f}\n⚙️ **Майнишь:** {cn}", parse_mode="Markdown", reply_markup=mining_menu())

@router.message(F.text.contains("Вывести в портфель"))
async def w_crypto(m: Message):
    p = await get_player(m.from_user.id)
    b, e, d = p[21], p[22], p[25]
    if b == 0 and e == 0 and d == 0: return await m.answer("❌ Нет крипты.")
    async with aiosqlite.connect(DB_PATH) as db:
        if b > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'BTC', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (m.from_user.id, b, b))
        if e > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'ETH', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (m.from_user.id, e, e))
        if d > 0: await db.execute("INSERT INTO market_portfolio (user_id, symbol, amount) VALUES (?, 'DOGE', ?) ON CONFLICT(user_id, symbol) DO UPDATE SET amount = amount + ?", (m.from_user.id, d, d))
        await db.execute("UPDATE players SET crypto_btc = 0, crypto_eth = 0, crypto_doge = 0 WHERE user_id=?", (m.from_user.id,))
        await db.commit()
    await m.answer(f"✅ Выведено: BTC {b:.6f}, ETH {e:.6f}, DOGE {d:.4f}")

@router.message(F.text.contains("Продать детали"))
async def s_parts(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sp.id, sp.name, i.amount, i.cond, sp.price FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=?", (m.from_user.id,)) as c: items = await c.fetchall()
    if not items: return await m.answer("📦 Пусто.")
    t, k = "💸 **Продажа**\n\n", []
    for i in items:
        pr = int(i[4] * 0.5 * (i[3] / 100.0))
        t += f"▪️ **{i[1]}** (x{i[2]})\nИзнос: {i[3]:.1f}% | Цена: {pr} 💰\n\n"
        k.append([InlineKeyboardButton(text=f"Продать {i[1]} (+{pr}💰)", callback_data=f"sp_{i[0]}")])
    await m.answer(t, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("sp_"))
async def s_p(c: CallbackQuery):
    pid = int(c.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT i.amount, i.cond, sp.price, sp.name FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=? AND i.part_id=?", (c.from_user.id, pid)) as cur: r = await cur.fetchone()
        if not r or r[0] <= 0: return await c.answer("Нет детали.")
        pr = int(r[2] * 0.5 * (r[1] / 100.0))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (c.from_user.id, pid))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (pr, c.from_user.id))
        await db.commit()
    await c.message.answer(f"✅ Продано {r[3]} за {pr}!")
    try: await c.message.delete()
    except: pass

    @router.message(F.text.contains("Сменить монету"))
async def c_coin(m: Message):
    k = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BTC", callback_data="coin_BTC")],[InlineKeyboardButton(text="ETH", callback_data="coin_ETH")],[InlineKeyboardButton(text="DOGE", callback_data="coin_DOGE")]])
    await m.answer("Монета:", reply_markup=k)

@router.callback_query(F.data.startswith("coin_"))
async def set_c(c: CallbackQuery):
    coin = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET mining_coin=? WHERE user_id=?", (coin, c.from_user.id))
        await db.commit()
    await c.message.edit_text(f"✅ Майнишь {coin}")

@router.message(F.text.contains("Магазин деталей"))
async def shop(m: Message):
    if (await is_in_prison(m.from_user.id))[0]: return await m.answer("⛓ Тюрьма!")
    tp = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 БП", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    k = [[InlineKeyboardButton(text=n, callback_data=f"sc_{t}")] for t, n in tp.items()]
    await m.answer("🛒 **Магазин**:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("sc_"))
async def s_cat(c: CallbackQuery):
    cat = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, price, hashrate, wattage, slots FROM mining_shop WHERE part_type=?", (cat,)) as cur: parts = await cur.fetchall()
    t, k = f"📦 **Товары:**\n\n", []
    for p in parts:
        st = []
        if p[3] > 0: st.append(f"Хеш: +{p[3]}")
        if p[4] > 0: st.append(f"Ватт: {p[4]}")
        if p[5] > 0: st.append(f"Слотов: {p[5]}")
        t += f"**{p[1]}**\nЦена: {p[2]} 💰 | {', '.join(st)}\n\n"
        k.append([InlineKeyboardButton(text=f"Купить за {p[2]}", callback_data=f"bp_{p[0]}")])
    k.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sb")])
    await c.message.edit_text(t, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data == "sb")
async def s_back(c: CallbackQuery):
    tp = {"case": "📦 Корпуса", "mb": "🔲 Материнки", "psu": "🔌 БП", "cpu": "🧠 Процессоры", "gpu": "🎮 Видеокарты"}
    k = [[InlineKeyboardButton(text=n, callback_data=f"sc_{t}")] for t, n in tp.items()]
    await c.message.edit_text("🛒 **Магазин**:", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("bp_"))
async def b_p(c: CallbackQuery):
    pid = int(c.data.split("_")[1])
    p = await get_player(c.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name, price FROM mining_shop WHERE id=?", (pid,)) as cur: part = await cur.fetchone()
        if p[3] < part[1]: return await c.message.answer("Мало монет!")
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (part[1], c.from_user.id))
        await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, 1, 100.0) ON CONFLICT(user_id, part_id) DO UPDATE SET amount = amount + 1", (c.from_user.id, pid))
        await db.commit()
    await c.message.answer(f"✅ Куплено: {part[0]}")

async def _r_rigs(t):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name FROM mining_rigs WHERE user_id=?", (t.from_user.id,)) as cur: rigs = await cur.fetchall()
    tx, k = "🖥 **Фермы:**\n\n", []
    if not rigs: tx += "Нет ферм. Купи корпус!"
    else:
        for r in rigs: k.append([InlineKeyboardButton(text=f"🖥 {r[1]}", callback_data=f"rig_{r[0]}")])
    k.append([InlineKeyboardButton(text="➕ Создать", callback_data="cr")])
    if isinstance(t, CallbackQuery): await t.message.edit_text(tx, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))
    else: await t.answer(tx, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.message(F.text.contains("Мои фермы"))
async def m_rigs(m: Message):
    if (await is_in_prison(m.from_user.id))[0]: return await m.answer("⛓ Тюрьма!")
    await _r_rigs(m)

@router.callback_query(F.data == "br")
async def b_rigs(c: CallbackQuery):
    await _r_rigs(c)

@router.callback_query(F.data == "cr")
async def c_rig(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT i.part_id, s.name FROM mining_inventory i JOIN mining_shop s ON i.part_id = s.id WHERE i.user_id=? AND s.part_type='case'", (c.from_user.id,)) as cur: cases = await cur.fetchall()
    if not cases: return await c.message.answer("Нет корпусов!")
    k = [[InlineKeyboardButton(text=f"Создать: {x[1]}", callback_data=f"dcr_{x[0]}")] for x in cases]
    k.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="br")])
    await c.message.edit_text("Корпус:", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("dcr_"))
async def d_crt(c: CallbackQuery):
    pid = int(c.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM mining_shop WHERE id=?", (pid,)) as cur: nm = (await cur.fetchone())[0]
        await db.execute("INSERT INTO mining_rigs (user_id, name) VALUES (?, ?)", (c.from_user.id, nm))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (c.from_user.id, pid))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.commit()
    await c.message.answer("✅ Создана!")
    await _r_rigs(c)

async def _r_rig(t, rid):
    sql = "SELECT r.name, p_mb.name, p_mb.slots, p_psu.name, p_psu.wattage, p_cpu.name, p_cpu.hashrate FROM mining_rigs r LEFT JOIN mining_shop p_mb ON r.mb_id = p_mb.id LEFT JOIN mining_shop p_psu ON r.psu_id = p_psu.id LEFT JOIN mining_shop p_cpu ON r.cpu_id = p_cpu.id WHERE r.id=?"
    gsql = "SELECT SUM(sp.wattage * rg.amount), SUM(sp.hashrate * rg.amount), SUM(rg.amount) FROM mining_rig_gpus rg JOIN mining_shop sp ON rg.part_id = sp.id WHERE rg.rig_id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, (rid,)) as cur: rig = await cur.fetchone()
        async with db.execute(gsql, (rid,)) as cur: gpu = await cur.fetchone()
    sl, mw, ch = (rig[2] or 0), (rig[4] or 0), (rig[6] or 0)
    gc, tw, th = (gpu[2] or 0), (gpu[0] or 0), ch + (gpu[1] or 0)
    tx = f"🖥 **{rig[0]}**\n🔲 {rig[1] or '❌'} (Слот: {sl})\n🔌 {rig[3] or '❌'} (Лим: {mw}W)\n🧠 {rig[5] or '❌'}\n🎮 {gc}/{sl}\n⚡ {tw}/{mw}W\n📈 Хеш: {th:.4f}\n"
    if tw > mw and mw > 0: tx += "⚠️ **МАЛО БП!**"
    k = [[InlineKeyboardButton(text="Установить", callback_data=f"im_{rid}")],[InlineKeyboardButton(text="📊 Состояние", callback_data=f"cd_{rid}")],[InlineKeyboardButton(text="🗑 Снять", callback_data=f"rm_{rid}")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="br")]]
    if isinstance(t, CallbackQuery): await t.message.edit_text(tx, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))
    else: await t.answer(tx, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("rig_"))
async def r_cfg(c: CallbackQuery):
    await _r_rig(c, int(c.data.split("_")[1]))

@router.callback_query(F.data.startswith("cd_"))
async def s_cond(c: CallbackQuery):
    rid = int(c.data.split("_")[1])
    sql = "SELECT p_mb.name, r.mb_cond, p_psu.name, r.psu_cond, p_cpu.name, r.cpu_cond FROM mining_rigs r LEFT JOIN mining_shop p_mb ON r.mb_id = p_mb.id LEFT JOIN mining_shop p_psu ON r.psu_id = p_psu.id LEFT JOIN mining_shop p_cpu ON r.cpu_id = p_cpu.id WHERE r.id=?"
    gsql = "SELECT sp.name, rg.cond, rg.amount FROM mining_rig_gpus rg JOIN mining_shop sp ON rg.part_id = sp.id WHERE rg.rig_id=?"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, (rid,)) as cur: rig = await cur.fetchone()
        async with db.execute(gsql, (rid,)) as cur: gpus = await cur.fetchall()
    tx = "📊 **Состояние:**\n"
    if rig[0]: tx += f"🔲 {rig[0]}: {rig[1]:.1f}%\n"
    if rig[2]: tx += f"🔌 {rig[2]}: {rig[3]:.1f}%\n"
    if rig[4]: tx += f"🧠 {rig[4]}: {rig[5]:.1f}%\n"
    for g in gpus: tx += f"🎮 {g[0]} x{g[2]}: {g[1]:.1f}%\n"
    await c.message.edit_text(tx, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")]]))

@router.callback_query(F.data.startswith("rm_"))
async def r_menu(c: CallbackQuery):
    rid = int(c.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT mb_id, psu_id, cpu_id FROM mining_rigs WHERE id=?", (rid,)) as cur: rig = await cur.fetchone()
        async with db.execute("SELECT part_id, amount FROM mining_rig_gpus WHERE rig_id=?", (rid,)) as cur: gpus = await cur.fetchall()
    k = []
    if rig[0]: k.append([InlineKeyboardButton(text="Снять Мать", callback_data=f"rp_{rid}_mb")])
    if rig[1]: k.append([InlineKeyboardButton(text="Снять БП", callback_data=f"rp_{rid}_psu")])
    if rig[2]: k.append([InlineKeyboardButton(text="Снять Проц", callback_data=f"rp_{rid}_cpu")])
    for g in gpus: k.append([InlineKeyboardButton(text=f"Снять Вид (x{g[1]})", callback_data=f"rp_{rid}_gpu_{g[0]}")])
    if not k: return await c.message.edit_text("Пусто.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")]]))
    k.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")])
    await c.message.edit_text("Что снять?", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("rp_"))
async def r_part(c: CallbackQuery):
    p = c.data.split("_")
    rid, pt = int(p[1]), p[2]
    async with aiosqlite.connect(DB_PATH) as db:
        if pt in ("mb", "psu", "cpu"):
            sql = f"SELECT {pt}_id, {pt}_cond FROM mining_rigs WHERE id=?"
            async with db.execute(sql, (rid,)) as cur: row = await cur.fetchone()
            pid, cnd = (row[0] if row else 0), (row[1] if row else 100.0)
            if pid:
                await db.execute(f"UPDATE mining_rigs SET {pt}_id=0, {pt}_cond=100.0 WHERE id=?", (rid,))
                async with db.execute("SELECT amount, cond FROM mining_inventory WHERE user_id=? AND part_id=?", (c.from_user.id, pid)) as cur: inv = await cur.fetchone()
                if inv:
                    na, ac = inv[0] + 1, (inv[0] * inv[1] + cnd) / (inv[0] + 1)
                    await db.execute("UPDATE mining_inventory SET amount=?, cond=? WHERE user_id=? AND part_id=?", (na, ac, c.from_user.id, pid))
                else: await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, 1, ?)", (c.from_user.id, pid, cnd))
        elif pt == "gpu":
            pid = int(p[3])
            async with db.execute("SELECT amount, cond FROM mining_rig_gpus WHERE rig_id=? AND part_id=?", (rid, pid)) as cur: row = await cur.fetchone()
            amt, cnd = (row[0] if row else 0), (row[1] if row else 100.0)
            if amt > 0:
                await db.execute("DELETE FROM mining_rig_gpus WHERE rig_id=? AND part_id=?", (rid, pid))
                async with db.execute("SELECT amount, cond FROM mining_inventory WHERE user_id=? AND part_id=?", (c.from_user.id, pid)) as cur: inv = await cur.fetchone()
                if inv:
                    na, ac = inv[0] + amt, (inv[0] * inv[1] + amt * cnd) / (inv[0] + amt)
                    await db.execute("UPDATE mining_inventory SET amount=?, cond=? WHERE user_id=? AND part_id=?", (na, ac, c.from_user.id, pid))
                else: await db.execute("INSERT INTO mining_inventory (user_id, part_id, amount, cond) VALUES (?, ?, ?, ?)", (c.from_user.id, pid, amt, cnd))
        await db.commit()
    await c.message.answer("✅ Снято с износом!")
    await _r_rig(c, rid)

@router.callback_query(F.data.startswith("im_"))
async def i_menu(c: CallbackQuery):
    rid = int(c.data.split("_")[1])
    sql = "SELECT sp.id, sp.name, sp.part_type, i.amount, i.cond FROM mining_inventory i JOIN mining_shop sp ON i.part_id = sp.id WHERE i.user_id=? AND sp.part_type != 'case'"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, (c.from_user.id,)) as cur: items = await cur.fetchall()
    if not items: return await c.message.answer("Нет деталей!")
    k = [[InlineKeyboardButton(text=f"[{i[2].upper()}] {i[1]} (x{i[3]}, {i[4]:.0f}%)", callback_data=f"di_{rid}_{i[0]}")] for i in items]
    k.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rig_{rid}")])
    await c.message.edit_text("Деталь:", reply_markup=InlineKeyboardMarkup(inline_keyboard=k))

@router.callback_query(F.data.startswith("di_"))
async def d_inst(c: CallbackQuery):
    _, _, rid, pid = c.data.split("_")
    rid, pid = int(rid), int(pid)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT part_type, name FROM mining_shop WHERE id=?", (pid,)) as cur: pt, nm = await cur.fetchone()
        async with db.execute("SELECT cond FROM mining_inventory WHERE user_id=? AND part_id=?", (c.from_user.id, pid)) as cur: cnd = (await cur.fetchone())[0]
        if pt == 'gpu': await db.execute("INSERT INTO mining_rig_gpus (rig_id, part_id, amount, cond) VALUES (?, ?, 1, ?) ON CONFLICT(rig_id, part_id) DO UPDATE SET amount = amount + 1", (rid, pid, cnd))
        elif pt in ('mb', 'psu', 'cpu'): await db.execute(f"UPDATE mining_rigs SET {pt}_id=?, {pt}_cond=? WHERE id=?", (pid, cnd, rid))
        await db.execute("UPDATE mining_inventory SET amount = amount - 1 WHERE user_id=? AND part_id=?", (c.from_user.id, pid))
        await db.execute("DELETE FROM mining_inventory WHERE amount <= 0")
        await db.commit()
    await c.message.answer(f"✅ {nm} установлен (Износ: {cnd:.0f}%)!")
    await _r_rig(c, rid)
