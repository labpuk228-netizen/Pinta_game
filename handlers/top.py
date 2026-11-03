import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from database import DB_PATH

router = Router()

@router.message(F.text == "🏆 Топ игроков")
async def show_top(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username, balance FROM players ORDER BY balance DESC LIMIT 10") as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("Пока нет игроков.")
        return

    text = "🏆 **Топ-10 богачей:**\n\n"
    for i, r in enumerate(rows, 1):
        name = f"@{r[0]}" if r[0] and r[0] != "player" else "Игрок"
        text += f"{i}. {name} — {r[1]} монет\n"
    await message.answer(text, parse_mode="Markdown")
