import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import prop_menu

router = Router()

@router.message(F.text == "🏠 Жильё")
async def prop_main(message: Message):
    await message.answer("🏠 **Недвижимость**\nВыбери действие снизу:", reply_markup=prop_menu())

@router.message(F.text == "🏘 Вся недвижимость")
async def show_properties(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, rent, buy, comfort FROM properties WHERE id > 0") as cur:
            props = await cur.fetchall()

    text = "🏘 **Доступная недвижимость:**\n\n"
    kb = []
    for p in props:
        text += f"**{p[1]}** (Комфорт: {p[4]})\nАренда: {p[2]} | Покупка: {p[3]}\n\n"
        kb.append([
            InlineKeyboardButton(text=f"Снять {p[1]}", callback_data=f"rent_{p[0]}"),
            InlineKeyboardButton(text=f"Купить {p[1]}", callback_data=f"buyprop_{p[0]}")
        ])
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("rent_"))
async def rent_prop(callback: CallbackQuery):
    prop_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET property_id=? WHERE user_id=?", (prop_id, callback.from_user.id))
        await db.commit()
    await callback.answer("✅ Жильё снято! Аренда будет списываться каждые 5 минут.", show_alert=True)
    await callback.message.delete()

@router.callback_query(F.data.startswith("buyprop_"))
async def buy_prop(callback: CallbackQuery):
    prop_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
        if player[3] < prop[1]:
            await callback.answer(f"Недостаточно средств! Нужно {prop[1]}.", show_alert=True)
            return
        await db.execute("UPDATE players SET balance = balance - ?, property_id=? WHERE user_id=?", (prop[1], prop_id, callback.from_user.id))
        await db.commit()
    await callback.answer(f"🏠 Ты купил {prop[0]}!", show_alert=True)
    await callback.message.delete()

@router.message(F.text == "🏠 Моё жильё")
async def my_prop(message: Message):
    player = await get_player(message.from_user.id)
    if player[7] == 0: # ИСПРАВЛЕНО: 7
        await message.answer("Ты живешь на улице. Сними или купи жильё!")
        return
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, rent, comfort FROM properties WHERE id=?", (player[7],)) as cur: # ИСПРАВЛЕНО: 7
            prop = await cur.fetchone()
            
    text = f"🏠 **Твоё жильё: {prop[0]}**\nКомфорт: {prop[2]}\nАренда: {prop[1]}\n"
    kb = [[InlineKeyboardButton(text="Сдать NPC-жильцу (+доход)", callback_data="rent_npc")]]
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "rent_npc")
async def rent_to_npc(callback: CallbackQuery):
    await callback.answer("🤝 NPC заселен! Теперь он будет платить тебе аренду каждые 5 минут (но может устроить потоп).", show_alert=True)
    await callback.message.delete()
