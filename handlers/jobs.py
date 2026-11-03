import aiosqlite, random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import job_menu

router = Router()
PAGE_SIZE = 4

@router.message(F.text == "💼 Работа")
async def show_jobs_menu(message: Message):
    player = await get_player(message.from_user.id)
    if player[4] > 0:
        text = f"💼 **Твоя текущая работа**\nЗарплата: {player[4]} монет/цикл.\n\nВыбери действие снизу."
    else:
        text = "💼 **Биржа труда**\nТы пока безработный. Найди работу или подработай!"
    await message.answer(text, parse_mode="Markdown", reply_markup=job_menu())

@router.message(F.text == "📋 Вакансии")
async def list_jobs(message: Message):
    await render_jobs(message, 0)

async def render_jobs(target, page):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, salary, req_edu, req_prop FROM jobs") as cur:
            jobs = await cur.fetchall()
    
    start = page * PAGE_SIZE
    page_jobs = jobs[start:start+PAGE_SIZE]
    text = f"📋 **Вакансии (стр. {page+1})**\n\n"
    kb = []
    
    for j in page_jobs:
        req = []
        if j[3] > 0: req.append(f"🎓 Обр. {j[3]}")
        if j[4] > 0: req.append(f"🏠 Жильё {j[4]}")
        req_t = ", ".join(req) if req else "Без требований"
        text += f"**{j[1]}** — {j[2]} 💰 (Нужно: {req_t})\n"
        kb.append([InlineKeyboardButton(text=f"Устроиться: {j[1]}", callback_data=f"takejob_{j[0]}")])
        
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_jobs_{page-1}"))
    if start + PAGE_SIZE < len(jobs): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_jobs_{page+1}"))
    if nav: kb.append(nav)
    
    if isinstance(target, Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("page_jobs_"))
async def paginate_jobs(callback: CallbackQuery):
    await render_jobs(callback, int(callback.data.split("_")[2]))
    await callback.answer()

@router.callback_query(F.data.startswith("takejob_"))
async def take_job(callback: CallbackQuery):
    job_id = int(callback.data.split("_")[1])
    player = await get_player(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, salary, req_edu, req_prop FROM jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
        
        # ИСПРАВЛЕНО: edu - это 8, prop - это 7
        if player[8] < job[2]:
            await callback.answer("Не хватает образования! Загляни в раздел 🎓 Образование.", show_alert=True)
            return
        if player[7] < job[3]:
            await callback.answer("Твоё жильё слишком плохое для этой работы!", show_alert=True)
            return
            
        await db.execute("UPDATE players SET job_salary=? WHERE user_id=?", (job[1], callback.from_user.id))
        await db.commit()
    await callback.message.edit_text(f"✅ Ты устроился на работу: **{job[0]}**!\nЗарплата будет приходить каждые 5 минут.", parse_mode="Markdown")
    await callback.answer("Успешно!")

@router.message(F.text == "🛠 Подработки")
async def list_side_jobs(message: Message):
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, min_e, max_e, cooldown, req_edu, req_prop, (SELECT last_done FROM side_cooldowns WHERE user_id=? AND job_id=side_jobs.id) FROM side_jobs", (message.from_user.id,)) as cur:
            jobs = await cur.fetchall()
    
    text = "🛠 **Доступные подработки:**\n\n"
    kb = []
    now = datetime.utcnow()
    
    for j in jobs:
        can_do, status = True, []
        # ИСПРАВЛЕНО: edu - это 8, prop - это 7
        if player[8] < j[5]: can_do = False; status.append(f"🎓{j[5]}")
        if player[7] < j[6]: can_do = False; status.append(f"🏠{j[6]}")
        
        if j[7] and can_do:
            last = datetime.strptime(j[7], "%Y-%m-%d %H:%M:%S")
            if now - last < timedelta(minutes=j[4]):
                can_do = False
                rem = timedelta(minutes=j[4]) - (now - last)
                status.append(f"⏳{int(rem.total_seconds()//60)}м")
                
        req = f" ({', '.join(status)})" if status else ""
        text += f"**{j[1]}** — {j[2]}-{j[3]} 💰{req}\n"
        if can_do:
            kb.append([InlineKeyboardButton(text=f"Выполнить", callback_data=f"doside_{j[0]}")])
            
    await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("doside_"))
async def do_side(callback: CallbackQuery):
    job_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, min_e, max_e FROM side_jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
        earn = random.randint(job[1], job[2])
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (earn, callback.from_user.id))
        await db.execute("INSERT OR REPLACE INTO side_cooldowns VALUES (?, ?, CURRENT_TIMESTAMP)", (callback.from_user.id, job_id))
        await db.commit()
    await callback.answer(f"💪 Заработано {earn} монет!", show_alert=True)
    await callback.message.delete()
