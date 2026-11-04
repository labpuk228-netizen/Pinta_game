import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player: return
    
    # ПРАВИЛЬНЫЕ ИНДЕКСЫ
    prop_id = player[7]
    edu = player[8]
    last_online = player[6]
    rep = player[19] if len(player) > 19 else 100
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title FROM properties WHERE id=?", (prop_id,)) as cur:
            prop = await cur.fetchone()
            prop_title = prop[0] if prop else "На улице"
            
        # Ищем бизнесы в новой таблице
        async with db.execute("SELECT b.title, pb.level FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.user_id=?", (message.from_user.id,)) as cur:
            bizs = await cur.fetchall()
            
    biz_text = "Нет"
    if bizs:
        biz_text = ", ".join([f"{b[0]} (Ур.{b[1]})" for b in bizs])
        if len(biz_text) > 50: biz_text = biz_text[:47] + "..."

    await message.answer(
        f"👤 **Твой профиль**\n\n"
        f"🆔 Личный код: `{player[2]}`\n"
        f"💰 Баланс: {player[3]} монет\n"
        f"💼 Зарплата: {player[4]} монет/цикл\n"
        f"🏠 Жильё: {prop_title}\n"
        f"🏢 Бизнесы: {biz_text}\n"
        f"🎓 Образование: Уровень {edu}\n"
        f"🏅 Репутация: {rep}\n"
        f"🕒 Последний вход: {last_online}",
        parse_mode="Markdown"
    )
