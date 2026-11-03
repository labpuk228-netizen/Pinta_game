import aiosqlite
import random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import section_menu

router = Router()
PAGE_SIZE = 4

@router.message(F.text == "💼 Работа")
async def show_jobs(message: Message):
    await _render_jobs_menu(message, 0)

async def _render_jobs_menu(target, page):
    player = await get_player(target.from_user.id)
    if not player: return
    
    # Если игрок уже работает
    if player[4] > 0:
        text = f"💼 **Твоя текущая работа**\nЗарплата: {player[4]} монет/цикл."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛠 Подработки", callback_data="side_page_0")],
            [InlineKeyboardButton(text="❌ Уволиться", callback_data="quit_job")]
        ])
        if isinstance(target, Message):
            await target.answer(text, parse_mode="Markdown", reply_markup=kb)
            await target.answer("Навигация:", reply_markup=section_menu())
        else:
            await target.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    # Если безработный — показываем вакансии
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, salary, required_education, required_property FROM jobs") as cur:
            jobs = await cur.fetchall()

    start = page * PAGE_SIZE
    page_jobs = jobs[start:start+PAGE_SIZE]
    
    text = f"💼 **Биржа труда** (стр. {page+1})\n\n"
    kb = []
    for j in page_jobs:
        req_text = []
        if j[3] > 0: req_text.append(f"🎓{j[3]}")
        if j[4] > 0: req_text.append(f"🏠{j[4]}")
        req = ", ".join(req_text) if req_text else "Без требований"
        text += f"**{j[1]}** — {j[2]} 💰 ({req})\n\n"
        kb.append([InlineKeyboardButton(text=f"Устроиться: {j[1]}", callback_data=f"job_{j[0]}")])

    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"jobs_page_{page-1}"))
    if start + PAGE_SIZE < len(jobs): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"jobs_page_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="🛠 Подработки", callback_data="side_page_0")])

    if isinstance(target, Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await target.answer("Навигация:", reply_markup=section_menu())
    else:
        await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("jobs_page_"))
async def jobs_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await _render_jobs_menu(callback, page)
    await callback.answer()

# --- ПОДРАБОТКИ ---
@router.callback_query(F.data.startswith("side_page_"))
async def show_side_jobs(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    player = await get_player(callback.from_user.id)
    edu, prop = player[7], player[6]
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT id, title, min_earning, max_earning, cooldown_minutes, required_education, required_property, 
            (SELECT last_done FROM side_jobs_cooldown WHERE user_id=? AND side_job_id=side_jobs.id) 
            FROM side_jobs ORDER BY min_earning ASC
        """, (callback.from_user.id,)) as cur:
            jobs = await cur.fetchall()
    
    start = page * PAGE_SIZE
    page_jobs = jobs[start:start+PAGE_SIZE]
    
    text = f"🛠 **Подработки** (стр. {page+1})\n\n"
    kb = []
    now = datetime.utcnow()
    
    for j in page_jobs:
        can_do, status = True, []
        if edu < j[5]: can_do = False; status.append(f"🎓{j[5]}")
        if prop < j[6]: can_do = False; status.append(f"🏠{j[6]}")
        
        if j[7] and can_do:
            last = datetime.strptime(j[7], "%Y-%m-%d %H:%M:%S")
            cd = timedelta(minutes=j[4])
            if now - last < cd:
                can_do = False
                rem = cd - (now - last)
                status.append(f"⏳{int(rem.total_seconds()//60)}м")
        
        req = f" ({', '.join(status)})" if status else ""
        text += f"**{j[1]}** — {j[2]}-{j[3]} 💰{req}\n"
        
        if can_do:
            kb.append([InlineKeyboardButton(text=f"▶️ {j[1]}", callback_data=f"do_side_{j[0]}")])
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"side_page_{page-1}"))
    if start + PAGE_SIZE < len(jobs): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"side_page_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="⬅️ К работам", callback_data="jobs_page_0")])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("do_side_"))
async def do_side_job(callback: CallbackQuery):
    job_id = int(callback.data.split("_")[2])
    player = await get_player(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, min_earning, max_earning FROM side_jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
        
        earnings = random.randint(job[1], job[2])
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (earnings, callback.from_user.id))
        await db.execute("INSERT OR REPLACE INTO side_jobs_cooldown (user_id, side_job_id, last_done) VALUES (?, ?, CURRENT_TIMESTAMP)", (callback.from_user.id, job_id))
        await db.commit()
    
    # Показываем короткое всплывающее уведомление и обновляем меню (без кнопки ОК)
    await callback.answer(f"💪 {job[0]}: заработал {earnings} монет!")
    await show_side_jobs(callback)

# --- ОСТАЛЬНЫЕ ДЕЙСТВИЯ ---
@router.callback_query(F.data == "quit_job")
async def quit_job(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET job_salary = 0 WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.message.edit_text("❌ Ты уволился. Нажми «💼 Работа» в меню, чтобы найти новую!")
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
            
        if player[7] < job[2]:
            await callback.answer("Не хватает образования!", show_alert=True)
            return
        if player[6] < job[3]:
            await callback.answer("Жильё слишком плохое для этой должности!", show_alert=True)
            return
            
        await db.execute("UPDATE players SET job_salary=? WHERE user_id=?", (job[1], callback.from_user.id))
        await db.commit()
    
    # ТЕПЕРЬ ЗДЕСЬ ЕСТЬ parse_mode="Markdown" - звездочки исчезнут
    await callback.message.edit_text(f"✅ Ты устроился на работу: **{job[0]}**!", parse_mode="Markdown")
    await callback.answer("Успешно!")
