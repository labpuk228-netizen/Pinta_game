import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🏠 Жильё")
async def show_property(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        return
    prop_id = player[7] if len(player) > 7 else 0

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, rent_cost, buy_cost FROM properties") as cur:
            props = await cur.fetchall()

    text = "🏠 **Недвижимость**\n\n"
    for p in props:
        if p[0] == 0: continue
        status = "✅ (Текущее)" if p[0] == prop_id else ""
        text += f"ID: {p[0]} | {p[1]} {status}\n"
        text += f"Аренда: {p[2]} монет/цикл | Покупка: {p[3]} монет\n\n"
    
    text += "Чтобы снять жильё, напиши: `/rent 1` (где 1 - ID жилья)\n"
    text += "Чтобы купить жильё, напиши: `/buyhome 1`"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text.startswith("/rent "))
async def rent_property(message: Message):
    try:
        prop_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Формат: /rent 1")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
        if not prop:
            await message.answer("Жилье с таким ID не найдено.")
            return
        await db.execute("UPDATE players SET property_id=? WHERE user_id=?", (prop_id, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ты снял жилье: {prop[0]}. Теперь каждый цикл будет списываться аренда.")

@router.message(F.text.startswith("/buyhome "))
async def buy_property(message: Message):
    try:
        prop_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Формат: /buyhome 1")
        return
    
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, buy_cost FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
        if not prop:
            await message.answer("Жилье с таким ID не найдено.")
            return
        if player[3] < prop[1]:
            await message.answer(f"Недостаточно средств! Нужно {prop[1]} монет.")
            return
        
        await db.execute("UPDATE players SET balance = balance - ?, property_id=0 WHERE user_id=?", (prop[1], message.from_user.id))
        await db.commit()
    await message.answer(f"🏠 Поздравляю! Ты купил {prop[0]}. Аренда больше не списывается.")
