import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🏢 Бизнесы")
async def show_businesses(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT business_id FROM players WHERE user_id=?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            my_biz_id = row[0] if row else 0

        async with db.execute("SELECT id, title, buy_cost, passive_income, upkeep_cost FROM businesses") as cur:
            bizs = await cur.fetchall()

    text = "🏢 **Бизнесы**\n\n"
    if my_biz_id > 0:
        text += "✅ У тебя уже есть бизнес. Ты можешь купить только один.\n"
        await message.answer(text, parse_mode="Markdown")
        return

    keyboard = []
    for b in bizs:
        text += f"**{b[1]}**\nЦена: {b[2]} | Доход: +{b[3]} | Обслуживание: -{b[4]}\n\n"
        keyboard.append([InlineKeyboardButton(text=f"Купить: {b[1]}", callback_data=f"buybiz_{b[0]}")])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("buybiz_"))
async def buy_business_callback(callback: CallbackQuery):
    biz_id = int(callback.data.split("_")[1])
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT business_id, balance FROM players WHERE user_id=?", (callback.from_user.id,)) as cur:
            player = await cur.fetchone()
        
        if player[0] > 0:
            await callback.answer("У тебя уже есть бизнес.", show_alert=True)
            return

        async with db.execute("SELECT title, buy_cost FROM businesses WHERE id=?", (biz_id,)) as cur:
            biz = await cur.fetchone()
        
        if player[1] < biz[1]:
            await callback.answer(f"Недостаточно средств! Нужно {biz[1]} монет.", show_alert=True)
            return
        
        await db.execute("UPDATE players SET balance = balance - ?, business_id=? WHERE user_id=?", (biz[1], biz_id, callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"🏢 Поздравляю! Ты купил бизнес: {biz[0]}!", show_alert=True)
    await callback.message.delete()
