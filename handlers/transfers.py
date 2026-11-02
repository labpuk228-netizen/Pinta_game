import aiosqlite
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import DB_PATH

router = Router()


class TransferStates(StatesGroup):
    waiting_code = State()
    waiting_amount = State()


@router.message(F.text == "💸 Перевод")
async def start_transfer(message: Message, state: FSMContext):
    await message.answer("Введи код получателя (6 символов):")
    await state.set_state(TransferStates.waiting_code)


@router.message(TransferStates.waiting_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM players WHERE transfer_code=?", (code,)) as cur:
            row = await cur.fetchone()
    if not row:
        await message.answer("Игрок с таким кодом не найден.")
        await state.clear()
        return
    await state.update_data(recipient_id=row[0])
    await message.answer("Введи сумму перевода:")
    await state.set_state(TransferStates.waiting_amount)


@router.message(TransferStates.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("Введи целое число.")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    data = await state.get_data()
    sender_id = message.from_user.id
    recipient_id = data["recipient_id"]
    if sender_id == recipient_id:
        await message.answer("Нельзя перевести самому себе.")
        await state.clear()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM players WHERE user_id=?", (sender_id,)) as cur:
            balance = (await cur.fetchone())[0]
        if balance < amount:
            await message.answer("Недостаточно средств.")
            await state.clear()
            return
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (amount, sender_id))
        await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amount, recipient_id))
        await db.commit()
    await message.answer(f"✅ Переведено {amount} монет.")
    await state.clear()
