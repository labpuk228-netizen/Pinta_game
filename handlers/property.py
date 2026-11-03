import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🏠 Жильё")
async def show_property(message: Message):
    player = await get_player(message.from_user.id)
    if not player: return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, rent_cost, buy_cost FROM properties WHERE id > 0") as cur:
            props = await cur.fetchall()

    text = "🏠 **Недвижимость**\n\n"
    keyboard = []
    
    for p in props:
        text += f"**{p[1]}**\nАренда: {p[2]} монет/цикл\nПокупка: {p[3]} монет\n\n"
        keyboard.append([
            InlineKeyboardButton(text=f"Снять {p[1]}", callback_data=f"rent_{p[0]}"),
            InlineKeyboardButton(text=f"Купить {p[1]}", callback_data=f"buyhome_{p[0]}")
        ])

    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("rent_"))
async def rent_property_callback(callback: CallbackQuery):
    prop_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
        await db.execute("UPDATE players SET property_id=? WHERE user_id=?", (prop_id, callback.from_user.id))
        await db.commit()
    await callback.answer(f"Ты снял жилье: {prop[0]}.", show_alert=True)
    await callback.message.delete()

@router.callback_query(F.data.startswith("buyhome_"))
async def buy_property_callback(callback: CallbackQuery):
    prop_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy_cost FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
        
        if player[3] < prop[1]:
            await callback.answer(f"Недостаточно средств! Нужно {prop[1]} монет.", show_alert=True)
            return
        
        await db.execute("UPDATE players SET balance = balance - ?, property_id=0 WHERE user_id=?", (prop[1], callback.from_user.id))
        await db.commit()
    await callback.answer(f"🏠 Поздравляю! Ты купил {prop[0]}.", show_alert=True)
    await callback.message.delete()
