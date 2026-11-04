import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SECRET_ADMIN_CODE, ADMIN_ID
from database import DB_PATH, get_player
from keyboards import admin_menu, main_menu

router = Router()

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_player_id = State()
    waiting_amount = State()
    waiting_reply_ticket = State()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

@router.message(F.text == SECRET_ADMIN_CODE)
async def admin_entry(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("🛡 **Админ-панель активирована**", reply_markup=admin_menu())

@router.message(F.text == "🛡 Админ-панель")
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("🛠 Выбери действие:", reply_markup=admin_menu())

@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(balance) FROM players") as cur:
            res = await cur.fetchone()
    await message.answer(f"📊 **Статистика**\n\n👥 Игроков: {res[0]}\n💰 Монет в экономике: {res[1] or 0}")

# --- РАССЫЛКА ---
@router.message(F.text == "📢 Рассылка")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer("Введи текст для рассылки всем игрокам:")

@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM players") as cur:
            users = await cur.fetchall()
            
    count = 0
    for u in users:
        try:
            await message.bot.send_message(u[0], f"📢 **Объявление:**\n\n{message.text}")
            count += 1
        except: pass
    await message.answer(f"✅ Сообщение отправлено {count} игрокам.")
    await state.clear()

# --- ЖАЛОБЫ ---
@router.message(F.text == "📩 Жалобы")
async def admin_tickets(message: Message):
    if not await is_admin(message.from_user.id): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, user_id, message FROM support_tickets WHERE status='open'") as cur:
            tickets = await cur.fetchall()
            
    if not tickets:
        await message.answer("Нет активных жалоб.")
        return
        
    for t in tickets:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_t_{t[0]}_{t[1]}")]])
        await message.answer(f"Тикет #{t[0]}\nОт ID: {t[1]}\nТекст: {t[2]}", reply_markup=kb)

@router.callback_query(F.data.startswith("reply_t_"))
async def admin_reply_ticket(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    _, _, tid, uid = callback.data.split("_")
    await state.update_data(ticket_id=tid, user_id=uid)
    await state.set_state(AdminStates.waiting_reply_ticket)
    await callback.message.answer("Введи ответ для игрока:")
    await callback.answer()

@router.message(AdminStates.waiting_reply_ticket)
async def admin_send_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.bot.send_message(int(data['user_id']), f"📩 **Ответ поддержки:**\n\n{message.text}")
        await message.answer("✅ Ответ отправлен.")
    except:
        await message.answer("❌ Не удалось отправить (игрок заблокировал бота).")
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE support_tickets SET status='closed' WHERE id=?", (data['ticket_id'],))
        await db.commit()
    await state.clear()
