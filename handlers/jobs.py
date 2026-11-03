import aiosqlite, random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import job_menu

router = Router()
JOB_PAGE_SIZE = 4
SIDE_PAGE_SIZE = 5

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
    start = page * JOB_PAGE_SIZE
    page_jobs = jobs[start:start+JOB_PAGE_SIZE]
    text = f"📋 **Вакансии (стр. {page+1})**\n\n"
    kb = []
    for j in page_jobs:
        req = []
        if j[3] > 0: req.append(f"🎓 Ур.{j[3]}")
        if j[4] > 0: req.append(f"🏠 Ур.{j[4]}")
        req_t = ", ".join(req) if req else "Без требований"
        text += f"**{j[1]}** — {j[2]} 💰 (Нужно: {req_t})\n"
        kb.append([InlineKeyboardButton(text=f"Устроиться: {j[1]}", callback_data=f"takejob_{j[0]}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_jobs_{page-1}"))
    if start + JOB_PAGE_SIZE < len(jobs): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_jobs_{page+1}"))
    if nav: kb.append(nav)
    if isinstance(target, Message): await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
        if player[8] < job[2]:
            await callback.answer() # Убрали show_alert
            await callback.message.answer(f"❌ Не хватает образования! Нужен Ур. {job[2]}.")
            return
        if player[7] < job[3]:
            await callback.answer()
            await callback.message.answer(f"❌ Твоё жильё слишком плохое! Нужно Ур. {job[3]}.")
            return
        await db.execute("UPDATE players SET job_salary=? WHERE user_id=?", (job[1], callback.from_user.id))
        await db.commit()
    await callback.message.edit_text(f"✅ Ты устроился на работу: **{job[0]}**!\nЗарплата будет приходить каждые 5 минут.", parse_mode="Markdown")
    await callback.answer()

@router.message(F.text == "🛠 Подработки")
async def list_side_jobs(message: Message):
    await render_side_jobs(message, 0)

async def render_side_jobs(target, page, earned_msg=""):
    player = await get_player(target.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, min_e, max_e, cooldown, req_edu, req_prop, no_cooldown_edu, (SELECT last_done FROM side_cooldowns WHERE user_id=? AND job_id=side_jobs.id) FROM side_jobs", (target.from_user.id,)) as cur:
            jobs = await cur.fetchall()
    start = page * SIDE_PAGE_SIZE
    page_jobs = jobs[start:start+SIDE_PAGE_SIZE]
    text = f"🛠 **Доступные подработки** (стр. {page+1})\n\n"
    if earned_msg: text = f"✅ {earned_msg}\n\n" + text
    kb = []
    now = datetime.utcnow()
    for j in page_jobs:
        can_do = True
        status = []
        if player[8] < j[5]: can_do = False; status.append(f"🎓{j[5]}")
        if player[7] < j[6]: can_do = False; status.append(f"🏠{j[6]}")
        has_cd = False
        if j[8] and player[8] < j[7]:
            last = datetime.strptime(j[8], "%Y-%m-%d %H:%M:%S")
            if now - last < timedelta(minutes=j[4]):
                has_cd = True
                can_do = False
                rem = timedelta(minutes=j[4]) - (now - last)
                status.append(f"⏳{int(rem.total_seconds()//60)}м")
        req = f" ({', '.join(status)})" if status else ""
        text += f"**{j[1]}** — {j[2]}-{j[3]} 💰{req}\n"
        if can_do: kb.append([InlineKeyboardButton(text=f"▶️ {j[1]}", callback_data=f"doside_{j[0]}_{page}")])
        elif has_cd: kb.append([InlineKeyboardButton(text=f"⏳ {j[1]} (Отдых)", callback_data="noop")])
        else: kb.append([InlineKeyboardButton(text=f"🔒 {j[1]} (Требования)", callback_data="noop")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"sidepage_{page-1}"))
    if start + SIDE_PAGE_SIZE < len(jobs): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"sidepage_{page+1}"))
    if nav: kb.append(nav)
    if isinstance(target, Message): await target.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await target.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("sidepage_"))
async def paginate_side(callback: CallbackQuery):
    await render_side_jobs(callback, int(callback.data.split("_")[1]))
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("doside_"))
async def do_side(callback: CallbackQuery):
    parts = callback.data.split("_")
    job_id, page = int(parts[1]), int(parts[2])
    player = await get_player(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, min_e, max_e, no_cooldown_edu FROM side_jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
        earn = random.randint(job[1], job[2])
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (earn, callback.from_user.id))
        if player[8] < job[3]:
            await db.execute("INSERT OR REPLACE INTO side_cooldowns VALUES (?, ?, CURRENT_TIMESTAMP)", (callback.from_user.id, job_id))
        await db.commit()
    await callback.answer()
    await render_side_jobs(callback, page, earned_msg=f"Ты заработал **{earn} монет** на задании «{job[0]}»!")
