import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "🎓 Образование")
async def show_education(message: Message):
    player = await get_player(message.from_user.id)
    if not player: return
    current_edu = player[8] if len(player) > 8 else 0

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, cost, level FROM educations") as cur:
            edus = await cur.fetchall()

    text = f"🎓 **Образование**\nТвой текущий уровень: {current_edu}\n\n"
    keyboard = []
    
    for e in edus:
        text += f"**{e[1]}** — Цена: {e[2]} монет (Уровень {e[3]})\n"
        if current_edu < e[3]:
            keyboard.append([InlineKeyboardButton(text=f"Купить: {e[1]}", callback_data=f"study_{e[0]}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    await message.answer(text, parse_mode="Markdown", reply_markup=reply_markup)

@router.callback_query(F.data.startswith("study_"))
async def study_callback(callback: CallbackQuery):
    edu_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, cost, level FROM educations WHERE id=?", (edu_id,)) as cur:
            edu = await cur.fetchone()
        
        if player[3] < edu[1]:
            await callback.answer(f"Недостаточно средств! Нужно {edu[1]} монет.", show_alert=True)
            return
        
        await db.execute("UPDATE players SET balance = balance - ?, education_level=? WHERE user_id=?", (edu[1], edu[2], callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"🎓 Ты прошел курс: {edu[0]}!", show_alert=True)
    await callback.message.delete()
