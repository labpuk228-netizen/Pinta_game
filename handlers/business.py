import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import biz_menu

router = Router()

@router.message(F.text.contains("Бизнесы"))
async def biz_main(message: Message):
    await message.answer("🏢 **Бизнесы**\nВыбери действие снизу:", reply_markup=biz_menu())

@router.message(F.text.contains("Купить бизнес"))
async def show_biz_shop(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, buy, income, upkeep FROM businesses") as cur:
            bizs = await cur.fetchall()

    text = "💼 **Доступные бизнесы (можно купить несколько):**\n\n"
    kb = []
    for b in bizs:
        text += f"**{b[1]}**\nЦена: {b[2]} | Доход: +{b[3]} | Обслуживание: -{b[4]}\n\n"
        kb.append([InlineKeyboardButton(text=f"Купить: {b[1]} ({b[2]}💰)", callback_data=f"buybiz_{b[0]}")])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("buybiz_"))
async def buy_biz(callback: CallbackQuery):
    biz_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM businesses WHERE id=?", (biz_id,)) as cur:
            biz = await cur.fetchone()
            
        if player[3] < biz[1]:
            # Вместо алерта просто шлем текст
            await callback.message.answer(f"❌ Недостаточно средств! Нужно {biz[1]} монет.")
            return
            
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (biz[1], callback.from_user.id))
        await db.execute("INSERT INTO player_businesses (user_id, business_id) VALUES (?, ?)", (callback.from_user.id, biz_id))
        await db.commit()
        
    await callback.message.answer(f"🏢 Куплен бизнес: **{biz[0]}**! Он добавлен в твой список.", parse_mode="Markdown")

# --- СПИСОК МОИХ БИЗНЕСОВ ---
@router.message(F.text.contains("Мои бизнесы"))
async def my_biz_list(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT pb.id, b.title, pb.level FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.user_id=?", (message.from_user.id,)) as cur:
            my_bizs = await cur.fetchall()
            
    if not my_bizs:
        await message.answer("У тебя пока нет бизнесов. Купи их во вкладке 'Купить бизнес'.")
        return
        
    text = "🏢 **Твои бизнесы:**\n(Выбери, чтобы управлять)\n\n"
    kb = []
    for b in my_bizs:
        text += f"▪️ {b[1]} (Ур. {b[2]})\n"
        kb.append([InlineKeyboardButton(text=f"⚙️ Управлять: {b[1]} (Ур.{b[2]})", callback_data=f"managebiz_{b[0]}")])
        
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- УПРАВЛЕНИЕ БИЗНЕСОМ ---
async def _render_biz_manage(target, pb_id, error_msg=""):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT pb.level, pb.staff, pb.boost, b.title, b.buy, b.income, b.upkeep FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.id=? AND pb.user_id=?", (pb_id, target.from_user.id)) as cur:
            biz = await cur.fetchone()
            
    if not biz:
        if isinstance(target, CallbackQuery): await target.message.edit_text("Бизнес не найден.")
        return

    lvl, staff, boost_time, title, base_buy, base_inc, base_up = biz
    
    income = base_inc * lvl
    staff_bonus = int(income * 0.2) * staff
    upkeep = base_up * lvl
    
    boost_active = False
    if boost_time:
        try:
            if datetime.utcnow() < datetime.strptime(boost_time, "%Y-%m-%d %H:%M:%S"): boost_active = True
        except: pass
        
    boost_bonus = int(income * 0.5) if boost_active else 0
    profit = (income + staff_bonus + boost_bonus) - upkeep
    
    text = ""
    if error_msg: text += f"❌ {error_msg}\n\n"
        
    text += (
        f"🏢 **{title}** (Ур. {lvl})\n\n"
        f"📈 Базовый доход: +{income}\n"
        f"👥 Сотрудники: {staff} (Бонус: +{staff_bonus})\n"
    )
    if boost_active: text += f"🔥 Буст активен (+{boost_bonus})\n"
    text += f"\n📉 Обслуживание: -{upkeep}\n💰 **Прибыль:** {profit} монет/цикл\n"

    upg_cost = base_buy * lvl * 3
    hire_cost = 1000 * (staff + 1)
    sell_price = int(base_buy * 0.5 * lvl) # Продажа: 50% от стоимости + бонус за уровни
    
    kb = []
    if lvl < 5: kb.append([InlineKeyboardButton(text=f"Улучшить до Ур.{lvl+1} ({upg_cost}💰)", callback_data=f"b_up_{pb_id}")])
    else: kb.append([InlineKeyboardButton(text="Максимальный уровень", callback_data="noop")])
        
    if staff < 5: kb.append([InlineKeyboardButton(text=f"Нанять NPC ({hire_cost}💰)", callback_data=f"b_hr_{pb_id}")])
    else: kb.append([InlineKeyboardButton(text="Максимум сотрудников", callback_data="noop")])
        
    if not boost_active: kb.append([InlineKeyboardButton(text=f"Расходники +50% (5000💰)", callback_data=f"b_bs_{pb_id}")])
    else: kb.append([InlineKeyboardButton(text="Буст уже активен", callback_data="noop")])
    
    kb.append([InlineKeyboardButton(text=f"💸 Продать бизнес (+{sell_price}💰)", callback_data=f"b_sl_{pb_id}")])
    kb.append([InlineKeyboardButton(text="⬅️ К списку бизнесов", callback_data="back_mybiz")])

    if isinstance(target, CallbackQuery): await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("managebiz_"))
async def manage_biz(callback: CallbackQuery):
    pb_id = int(callback.data.split("_")[1])
    await _render_biz_manage(callback, pb_id)
    await callback.answer()

@router.callback_query(F.data == "back_mybiz")
async def back_mybiz(callback: CallbackQuery):
    fake_msg = Message(message_id=callback.message.message_id, date=callback.message.date, chat=callback.message.chat, from_user=callback.from_user, text="Мои бизнесы")
    await my_biz_list(fake_msg)
    try: await callback.message.delete()
    except: pass
    await callback.answer()

# --- ДЕЙСТВИЯ ---
@router.callback_query(F.data.startswith("b_up_"))
async def b_up(callback: CallbackQuery):
    pb_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT pb.level, b.buy FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.id=? AND pb.user_id=?", (pb_id, callback.from_user.id)) as cur:
            lvl, buy = await cur.fetchone()
            
    cost = buy * lvl * 3
    player = await get_player(callback.from_user.id)
    if player[3] < cost:
        await _render_biz_manage(callback, pb_id, error_msg=f"Нужно {cost} монет!")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (cost, callback.from_user.id))
        await db.execute("UPDATE player_businesses SET level = level + 1 WHERE id=?", (pb_id,))
        await db.commit()
    await _render_biz_manage(callback, pb_id, error_msg=f"Улучшено до Ур. {lvl+1}!")

@router.callback_query(F.data.startswith("b_hr_"))
async def b_hr(callback: CallbackQuery):
    pb_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT staff FROM player_businesses WHERE id=? AND user_id=?", (pb_id, callback.from_user.id)) as cur:
            staff = (await cur.fetchone())[0]
            
    cost = 1000 * (staff + 1)
    player = await get_player(callback.from_user.id)
    if player[3] < cost:
        await _render_biz_manage(callback, pb_id, error_msg=f"Найм стоит {cost} монет!")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (cost, callback.from_user.id))
        await db.execute("UPDATE player_businesses SET staff = staff + 1 WHERE id=?", (pb_id,))
        await db.commit()
    await _render_biz_manage(callback, pb_id, error_msg=f"Сотрудник нанят!")

@router.callback_query(F.data.startswith("b_bs_"))
async def b_bs(callback: CallbackQuery):
    pb_id = int(callback.data.split("_")[2])
    player = await get_player(callback.from_user.id)
    if player[3] < 5000:
        await _render_biz_manage(callback, pb_id, error_msg="Расходники стоят 5000 монет!")
        return
        
    boost_until = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - 5000 WHERE user_id=?", (callback.from_user.id,))
        await db.execute("UPDATE player_businesses SET boost=? WHERE id=?", (boost_until, pb_id))
        await db.commit()
    await _render_biz_manage(callback, pb_id, error_msg="Закупка сделана! Буст на 15 минут.")

@router.callback_query(F.data.startswith("b_sl_"))
async def b_sl(callback: CallbackQuery):
    pb_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT pb.level, b.buy, b.title FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.id=? AND pb.user_id=?", (pb_id, callback.from_user.id)) as cur:
            lvl, buy, title = await cur.fetchone()
            
    sell_price = int(buy * 0.5 * lvl)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (sell_price, callback.from_user.id))
        await db.execute("DELETE FROM player_businesses WHERE id=?", (pb_id,))
        await db.commit()
        
    fake_msg = Message(message_id=callback.message.message_id, date=callback.message.date, chat=callback.message.chat, from_user=callback.from_user, text="Мои бизнесы")
    await my_biz_list(fake_msg)
    try: await callback.message.delete()
    except: pass
    await callback.message.answer(f"💸 Ты продал **{title}** за {sell_price} монет!", parse_mode="Markdown")

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
