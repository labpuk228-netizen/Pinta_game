import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import biz_menu

router = Router()

@router.message(F.text == "🏢 Бизнесы")
async def biz_main(message: Message):
    await message.answer("🏢 **Бизнесы**\nВыбери действие снизу:", reply_markup=biz_menu())

@router.message(F.text == "💼 Купить бизнес")
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
    if player[8] > 0:
        await callback.answer("У тебя уже есть бизнес. Ты можешь владеть только одним.", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM businesses WHERE id=?", (biz_id,)) as cur:
            biz = await cur.fetchone()
        if player[3] < biz[1]:
            await callback.answer(f"Недостаточно средств! Нужно {biz[1]}.", show_alert=True)
            return
        await db.execute("UPDATE players SET balance = balance - ?, business_id=?, business_level=1 WHERE user_id=?", (biz[1], biz_id, callback.from_user.id))
        await db.commit()
    await callback.answer(f"🏢 Поздравляю! Ты купил бизнес: {biz[0]}!", show_alert=True)
    await callback.message.delete()

@router.message(F.text == "🏢 Мои бизнесы")
async def my_biz(message: Message):
    player = await get_player(message.from_user.id)
    if player[8] == 0:
        await message.answer("У тебя пока нет бизнеса. Купи его во вкладке 'Купить бизнес'.")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, income, upkeep FROM businesses WHERE id=?", (player[8],)) as cur:
            biz = await cur.fetchone()
            
    lvl = player[9]
    total_income = biz[1] * lvl
    total_upkeep = biz[2] * lvl
    
    text = (
        f"🏢 **Твой бизнес: {biz[0]}** (Ур. {lvl})\n\n"
        f"📈 Доход: +{total_income} монет/цикл\n"
        f"📉 Обслуживание: -{total_upkeep} монет/цикл\n"
        f"💰 Чистая прибыль: {total_income - total_upkeep} монет/цикл"
    )
    kb = [[InlineKeyboardButton(text=f"Улучшить до Ур. {lvl+1} (Цена: {biz[1]*lvl*3})", callback_data="biz_upgrade")]]
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "biz_upgrade")
async def upgrade_biz(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[9] >= 5:
        await callback.answer("Максимальный уровень бизнеса достигнут!", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM businesses WHERE id=?", (player[8],)) as cur:
            biz = await cur.fetchone()
            
    cost = biz[1] * player[9] * 3
    if player[3] < cost:
        await callback.answer(f"Недостаточно средств для апгрейда! Нужно {cost}.", show_alert=True)
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ?, business_level = business_level + 1 WHERE user_id=?", (cost, callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"🚀 Бизнес улучшен до Ур. {player[9]+1}!", show_alert=True)
    await callback.message.delete()
