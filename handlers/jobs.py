import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import get_player, DB_PATH

router = Router()

@router.message(F.text == "💼 Работа")
async def show_jobs(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        return
    if player[4] > 0:
        await message.answer(f"Ты уже работаешь. Зарплата: {player[4]} монет/цикл.")
        return
    
    await message.answer(
        "Доступные вакансии:\n"
        "1. **Курьер** (200 монет/цикл) — без требований. Напиши `/work 1`\n"
        "2. **Грузчик** (150 монет/цикл) — без требований. Напиши `/work 2`\n"
        "3. **Программист** (800 монет/цикл) — нужно образование (Курсы IT). Напиши `/work 3`",
        parse_mode="Markdown"
    )

@router.message(F.text.startswith("/work "))
async def take_job(message: Message):
    try:
        job_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Формат: /work 1")
        return
        
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, salary, required_education FROM jobs WHERE id=?", (job_id,)) as cur:
            job = await cur.fetchone()
            
        if not job:
            await message.answer("Вакансия не найдена.")
            return
            
        edu_level = player[8] if len(player) > 8 else 0
        if edu_level < job[2]:
            await message.answer("У тебя недостаточно образования для этой работы! Загляни в раздел 🎓 Образование.")
            return
            
        await db.execute("UPDATE players SET job_salary=? WHERE user_id=?", (job[1], message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ты устроился на работу: {job[0]}! Зарплата будет приходить пассивно.")
