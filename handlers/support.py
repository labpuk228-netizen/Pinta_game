from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from database import DB_PATH
from config import ADMIN_ID

router = Router()

class SupportState(StatesGroup):
    waiting_msg = State()

@router.message(F.text == "📩 Поддержка")
async def support_start(message: Message, state: FSMContext):
    await state.set_state(SupportState.waiting_msg)
    await message.answer("✍️ Напиши свой вопрос или жалобу администратору (одним сообщением):")

@router.message(SupportState.waiting_msg)
async def support_send(message: Message, state: FSMContext):
    txt = message.text
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO support_tickets (user_id, message) VALUES (?, ?)", (message.from_user.id, txt))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cur:
            ticket_id = (await cur.fetchone())[0]
            
    await message.answer("✅ Сообщение отправлено! Админ скоро ответит.")
    await state.clear()
    
    try:
        await message.bot.send_message(ADMIN_ID, f"📩 **Новый тикет #{ticket_id}**\nОт: @{message.from_user.username} (ID: {message.from_user.id})\n\nТекст: {txt}")
    except: pass
