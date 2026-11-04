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

    text = "💼 **Доступные бизнесы:**\n\n"
    kb = []
    for b in bizs:
        text += f"**{b[1]}**\nЦена: {b[2]} | Доход: +{b[3]} | Обслуживание: -{b[4]}\n\n"
        kb.append([InlineKeyboardButton(text=f"Купить: {b[1]}", callback_data=f"buybiz_{b[0]}")])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("buybiz_"))
async def buy_biz(callback: CallbackQuery):
    biz_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    if player[9] > 0:
        await callback.answer("У тебя уже есть бизнес.", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM businesses WHERE id=?", (biz_id,)) as cur:
            biz = await cur.fetchone()
        if player[3] < biz[1]:
            await callback.answer(f"Недостаточно средств! Нужно {biz[1]}.", show_alert=True)
            return
        await db.execute("UPDATE players SET balance = balance - ?, business_id=?, business_level=1, business_staff=0, business_boost=NULL WHERE user_id=?", (biz[1], biz_id, callback.from_user.id))
        await db.commit()
    await callback.answer(f"🏢 Поздравляю! Ты купил бизнес: {biz[0]}!", show_alert=True)
    await callback.message.delete()

@router.message(F.text.contains("Мои бизнесы"))
async def my_biz(message: Message):
    player = await get_player(message.from_user.id)
    if player[9] == 0:
        await message.answer("У тебя пока нет бизнеса. Купи его во вкладке 'Купить бизнес'.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, income, upkeep FROM businesses WHERE id=?", (player[9],)) as cur:
            biz = await cur.fetchone()
            
    lvl = player[10]
    staff = player[11]
    boost_time = player[12]
    
    base_income = biz[1] * lvl
    staff_bonus = int(base_income * 0.2) * staff
    total_upkeep = biz[2] * lvl
    
    boost_active = False
    if boost_time:
        try:
            bt = datetime.strptime(boost_time, "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() < bt:
                boost_active = True
        except: pass
    
    boost_bonus = int(base_income * 0.5) if boost_active else 0
    final_income = base_income + staff_bonus + boost_bonus
    profit = final_income - total_upkeep
    
    text = (
        f"🏢 **{biz[0]}** (Ур. {lvl})\n\n"
        f"📈 Базовый доход: +{base_income} монет\n"
        f"👥 Сотрудники: {staff} (Бонус: +{staff_bonus} монет)\n"
    )
    if boost_active:
        text += f"🔥 Буст активен (+{boost_bonus} монет)\n"
        
    text += f"\n📉 Обслуживание: -{total_upkeep} монет\n💰 **Чистая прибыль:** {profit} монет/цикл\n"
    
    kb = [
        [InlineKeyboardButton(text=f"Улучшить до Ур. {lvl+1} (Цена: {biz[1]*lvl*3})", callback_data="biz_upgrade")],
        [InlineKeyboardButton(text="👥 Нанять NPC-сотрудника", callback_data="biz_hire")],
        [InlineKeyboardButton(text="🛒 Купить расходники (+50% на 3 цикла)", callback_data="biz_boost")]
    ]
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "biz_upgrade")
async def upgrade_biz(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[10] >= 5:
        await callback.answer("Максимальный уровень!", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM businesses WHERE id=?", (player[9],)) as cur:
            biz = await cur.fetchone()
            
    cost = biz[1] * player[10] * 3
    if player[3] < cost:
        await callback.answer(f"Нужно {cost} монет!", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ?, business_level = business_level + 1 WHERE user_id=?", (cost, callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"🚀 Бизнес улучшен до Ур. {player[10]+1}!", show_alert=True)
    await callback.message.delete()

@router.callback_query(F.data == "biz_hire")
async def hire_staff(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    
    if player[11] >= 5:
        await callback.answer("У тебя уже максимум сотрудников (5).", show_alert=True)
        return
        
    cost = 1000 * (player[11] + 1)
    if player[3] < cost:
        await callback.answer(f"Найм стоит {cost} монет!", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ?, business_staff = business_staff + 1 WHERE user_id=?", (cost, callback.from_user.id))
        await db.commit()
        
    await callback.answer(f"👥 Сотрудник нанят! Теперь их {player[11]+1}.", show_alert=True)
    await callback.message.delete()

@router.callback_query(F.data == "biz_boost")
async def buy_boost(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    
    cost = 5000
    if player[3] < cost:
        await callback.answer(f"Расходники стоят {cost} монет!", show_alert=True)
        return
        
    boost_until = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ?, business_boost=? WHERE user_id=?", (cost, boost_until, callback.from_user.id))
        await db.commit()
        
    await callback.answer("🛒 Закупка сделана! Доход увеличен на 50% на 3 цикла (15 минут).", show_alert=True)
    await callback.message.delete()
