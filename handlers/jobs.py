import aiosqlite
from aiogram import Router, F
from aiogram.types import Message

from database import get_player, DB_PATH

router = Router()


@router.message(F.text == "💼 Работа")
async def show_jobs(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала напиши /start")
        return
    if player[4] > 0:
        await message.answer(f"Ты уже работаешь. Зарплата: {player[4]} монет/цикл.")
        return
    await message.answer(
        "Доступна работа: **Курьер** (200 монет за цикл).\n"
        "Напиши /work чтобы устроиться.",
        parse_mode="Markdown"
    )


@router.message(F.text == "/work")
async def take_job(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала напиши /start")
        return
    if player[4] > 0:
        await message.answer("Ты уже работаешь.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET job_salary=200 WHERE user_id=?", (message.from_user.id,))
        await db.commit()
    await message.answer("✅ Ты устроился курьером! Зарплата будет приходить пассивно.")
