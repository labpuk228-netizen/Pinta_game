import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import section_menu

router = Router()
RIG_COST = 5000
RIG_HASHRATE = 0.01 # Дает 0.01 BTC за цикл

@router.message(F.text == "⛏️ Майнинг")
async def mining_menu(message: Message):
    player = await get_player(message.from_user.id)
    rigs = player[12]
    
    text = (
        f"⛏️ **Майнинг-ферма**\n\n"
        f"Твои фермы: {rigs} шт.\n"
        f"Доход: +{rigs * RIG_HASHRATE:.4f} BTC / цикл\n\n"
        f"Стоимость новой фермы: {RIG_COST} монет."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Купить ферму ({RIG_COST})", callback_data="mine_buy")],
        [InlineKeyboardButton(text="Продать ферму", callback_data="mine_sell")]
    ])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)
    await message.answer("Навигация:", reply_markup=section_menu())

@router.callback_query(F.data == "mine_buy")
async def buy_rig(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[3] < RIG_COST:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance - ?, mining_rigs = mining_rigs + 1 WHERE user_id=?", (RIG_COST, callback.from_user.id))
        await db.commit()
    
    await callback.answer("✅ Ферма куплена!", show_alert=True)
    # Обновляем сообщение
    player = await get_player(callback.from_user.id)
    rigs = player[12]
    text = (
        f"⛏️ **Майнинг-ферма**\n\n"
        f"Твои фермы: {rigs} шт.\n"
        f"Доход: +{rigs * RIG_HASHRATE:.4f} BTC / цикл\n\n"
        f"Стоимость новой фермы: {RIG_COST} монет."
    )
    await callback.message.edit_text(text, parse_mode="Markdown")

@router.callback_query(F.data == "mine_sell")
async def sell_rig(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player[12] <= 0:
        await callback.answer("У тебя нет ферм!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + ?, mining_rigs = mining_rigs - 1 WHERE user_id=?", (RIG_COST // 2, callback.from_user.id))
        await db.commit()
    
    await callback.answer(f"Продано за {RIG_COST // 2} монет (50% от цены).", show_alert=True)
    player = await get_player(callback.from_user.id)
    rigs = player[12]
    text = (
        f"⛏️ **Майнинг-ферма**\n\n"
        f"Твои фермы: {rigs} шт.\n"
        f"Доход: +{rigs * RIG_HASHRATE:.4f} BTC / цикл\n\n"
        f"Стоимость новой фермы: {RIG_COST} монет."
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
