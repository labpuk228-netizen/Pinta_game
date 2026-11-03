import aiosqlite
import random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "💼 Работа")
async def show_jobs(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        return
    
    if player[4] > 0:
        text = (
            f"💼 **Твоя текущая работа**\n\n"
            f"Зарплата: {player[4]} монет/цикл.\n\n"
            f"Ты можешь подработать или уволиться, чтобы найти что-то получше."
        )
        keyboard = [
            [InlineKeyboardButton(text="🛠 Подработать (быстрые деньги)", callback_data="side_job")],
            [InlineKeyboardButton(text="❌ Уволиться", callback_data="quit_job")]
        ]
        await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, salary, required_education, required_property FROM jobs") as cur:
            jobs = await cur.fetchall()

    text = "💼 **Биржа труда**\n\n"
    keyboard = [[InlineKeyboardButton(text="🛠 Подработать (быстрые деньги)", callback_data="side_job")]]

    for j in jobs:
        req_edu, req_prop = j[3], j[4]
        req_text = []
        if req_edu > 0: req_text.append(f"Образование ур.{req_edu}")
        if req_prop > 0: req_text.append(f"Жильё ур.{req_prop}")
        if not req_text: req_text.append("Без требований")

        text += f"**{j[1]}** — {j[2]} монет/цикл\n*(Требуется: {', '.join(req_text)})*\n\n"
        keyboard.append([InlineKeyboardButton(text=f"Устроиться: {j[1]}", callback_data=f"job_{j[0]}")])

    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "side_job")
async def process_side_job(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    last_job = player[10] if len(player) > 10 else None
    
    if last_job:
        last_time = datetime.strptime(last_job, "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        if now - last_time < timedelta(minutes=5):
            time_left = timedelta(minutes=5) - (now - last_time)
            minutes = int(time_left.total_seconds() // 60)
            seconds = int(time_left.total_seconds() % 60)
            await callback.answer(f"Ты устал. Отдохни ещё {minutes} мин {seconds} сек.", show_alert=True)
            return

    earnings = random.randint(80, 250)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ?, last_side_job = CURRENT_TIMESTAMP WHERE user_id=?", (earnings, callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"💪 Ты успешно подработал и получил {earnings} монет!", show_alert=True)

@router.callback_query(F.data == "quit_job")
async def quit_job(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET job_salary = 0 WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.message.edit_text("❌ Ты уволился. Теперь ты безработный. Нажми «💼 Работа» в меню, чтобы найти новую!")
    await callback.answer()

@router.callback_query(F.data.startswith("job_"))
async def take_job_callback(callback: CallbackQuery):
    job_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, salary, required_education, required_property FROM jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
            
        if not job:
            await callback.answer("Вакансия не найдена.", show_alert=True)
            return
            
        edu_level = player[8] if len(player) > 8 else 0
        prop_level = player[7] if len(player) > 7 else 0
        
        if edu_level < job[2]:
            await callback.answer(f"Тебе не хватает образования (нужно ур. {job[2]})!", show_alert=True)
            return
        if prop_level < job[3]:
            await callback.answer(f"Твоё жильё слишком плохое для этой должности (нужно жильё ур. {job[3]})!", show_alert=True)
            return
            
        await db.execute("UPDATE players SET job_salary=? WHERE user_id=?", (job[1], callback.from_user.id))
        await db.commit()
    
    await callback.message.edit_text(f"✅ Ты устроился на работу: **{job[0]}**!\nЗарплата будет приходить пассивно.")
    await callback.answer("Успешно!")
