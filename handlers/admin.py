import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from config import SECRET_ADMIN_CODE
from database import DB_PATH

router = Router()

@router.message(F.text == SECRET_ADMIN_CODE)
async def admin_entry(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (message.from_user.id,)) as cur:
            if not await cur.fetchone():
                await message.answer("⛔ Доступ запрещён.")
                return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, balance, last_online FROM players ORDER BY last_online DESC") as cur:
            rows = await cur.fetchall()
    if not rows:
        await message.answer("👥 Игроков пока нет.")
        return
    text = "👥 **Игроки:**\n\n" + "\n".join(
        f"• `{r[0]}` (@{r[1]}) — {r[2]} монет\n   был: {r[3]}" for r in rows[:30]
    )
    if len(rows) > 30:
        text += f"\n\n...и ещё {len(rows) - 30}"
    await message.answer(text, parse_mode="Markdown")
