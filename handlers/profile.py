import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text.contains("Профиль"))
async def show_profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player: 
        return
    
    # ИСПРАВЛЕННЫЕ ИНДЕКСЫ
    prop_id = player[7]
    edu = player[8]
    last_online = player[6]
    rep = player[19] if len(player) > 19 else 100
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
            prop_title = prop[0] if prop else "На улице"
            
        # Берем список бизнесов из новой таблицы
        async with db.execute("SELECT b.title, pb.level FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.user_id=?", (message.from_user.id,)) as cur:
            bizs = await cur.fetchall()
            
    biz_text = "Нет"
    if bizs:
        biz_text = ", ".join([f"{b[0]} (Ур.{b[1]})" for b in bizs])
        if len(biz_text) > 60: 
            biz_text = biz_text[:57] + "..."

    # Используем HTML, чтобы нижние подчеркивания в никах не ломали текст
    text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"🆔 Личный код: <code>{player[2]}</code>\n"
        f"💰 Баланс: {player[3]} монет\n"
        f"💼 Зарплата: {player[4]} монет/цикл\n"
        f"🏠 Жильё: {prop_title}\n"
        f"🏢 Бизнесы: {biz_text}\n"
        f"🎓 Образование: Уровень {edu}\n"
        f"🏅 Репутация: {rep}\n"
        f"🕒 Последний вход: {last_online}"
    )
    await message.answer(text, parse_mode="HTML")
