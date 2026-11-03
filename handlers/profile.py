import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player: return
    
    # ИСПРАВЛЕНО: правильные индексы новой БД
    prop_id = player[7]
    edu = player[8]
    biz_id = player[9]
    biz_lvl = player[10]
    last_online = player[6]
    rep = player[17]
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
            prop_title = prop[0] if prop else "На улице"
            
        async with db.execute("SELECT title FROM businesses WHERE id=?", (biz_id,)) as cur:
            biz = await cur.fetchone()
            biz_title = f"{biz[0]} (Ур. {biz_lvl})" if biz else "Нет"

    await message.answer(
        f"👤 **Твой профиль**\n\n"
        f"🆔 Личный код: `{player[2]}`\n"
        f"💰 Баланс: {player[3]} монет\n"
        f"💼 Зарплата: {player[4]} монет/цикл\n"
        f"🏠 Жильё: {prop_title}\n"
        f"🏢 Бизнес: {biz_title}\n"
        f"🎓 Образование: Уровень {edu}\n"
        f"🏅 Репутация: {rep}\n"
        f"🕒 Последний вход: {last_online}",
        parse_mode="Markdown"
        )
