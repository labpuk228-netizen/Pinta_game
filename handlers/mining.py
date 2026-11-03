import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_player, DB_PATH
from keyboards import mining_menu

router = Router()

@router.message(F.text == "⛏️ Майнинг")
async def mining_hub(message: Message):
    player = await get_player(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT SUM(sp.hashrate * rg.amount) 
            FROM mining_rig_gpus rg 
            JOIN mining_rigs r ON rg.rig_id = r.id 
            JOIN mining_shop sp ON rg.part_id = sp.id 
            WHERE r.user_id=?
        """, (message.from_user.id,)) as cur:
            total_hash = (await cur.fetchone())[0] or 0
            
    await message.answer(
        f"⛏️ **Майнинг-центр**\n\n"
        f"📈 Твой общий хешрейт: {total_hash:.4f}\n"
        f"🪙 Добыто BTC: {player[19]:.4f}\n\n"
        f"Управляй фермами и закупай комплектующие.",
        parse_mode="Markdown", reply_markup=mining_menu()
    )
# ... (остальной код mining.py оставляем без изменений, он был правильный)
