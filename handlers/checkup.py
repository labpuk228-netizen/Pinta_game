import aiosqlite
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import DB_PATH
from tasks.scheduler import scheduler, process_cycle

router = Router()

async def _test_core(respond_func, user_id: int):
    results = []
    errors = 0
    
    required_tables = ["players", "jobs", "properties", "educations", "businesses", "side_jobs", "crypto_assets", "admins"]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for table in required_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                        count = (await cur.fetchone())[0]
                        results.append(f"✅ БД `{table}`: {count} записей")
                except Exception:
                    results.append(f"❌ БД `{table}`: ОШИБКА")
                    errors += 1
    except Exception as e:
        results.append(f"❌ Нет доступа к БД: {e}")
        errors += 1
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM players WHERE user_id=?", (user_id,)) as cur:
                player = await cur.fetchone()
        if player:
            results.append("✅ Твой профиль в норме")
            results.append(f"   💰 Баланс: {player[3]}")
            results.append(f"   🏅 Репутация: {player[17]}")
            results.append(f"   🎲 Ставка: {player[27]}")
        else:
            results.append("❌ Профиль не найден (/start)")
            errors += 1
    except Exception as e:
        results.append(f"❌ Ошибка профиля: {e}")
        errors += 1
    
    if scheduler.running: results.append("✅ Планировщик работает")
    else: results.append("❌ Планировщик не запущен"); errors += 1
    
    if errors == 0: results.append("\n🎉 **Все тесты пройдены!**")
    else: results.append(f"\n⚠️ **Найдено проблем: {errors}**")
    
    text = "🧪 **Тестирование системы:**\n\n" + "\n".join(results)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Дать 10000 монет (тест)", callback_data="dev_give_money")],
        [InlineKeyboardButton(text="⚙️ Прогнать цикл", callback_data="dev_run_cycle")],
        [InlineKeyboardButton(text="🔄 Обновить тест", callback_data="dev_rerun")]
    ])
    
    await respond_func(text[:4000], parse_mode="Markdown", reply_markup=keyboard)

@router.message(F.text.contains("Тест"))
async def run_tests(message: Message):
    await _test_core(message.answer, message.from_user.id)

@router.callback_query(F.data == "dev_give_money")
async def give_money(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + 10000 WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.answer("💵 +10000 монет!", show_alert=True)

@router.callback_query(F.data == "dev_run_cycle")
async def run_cycle(callback: CallbackQuery):
    try:
        await process_cycle()
        await callback.answer("✅ Цикл выполнен!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "dev_rerun")
async def rerun_test(callback: CallbackQuery):
    try: await callback.message.delete()
    except: pass
    await _test_core(callback.message.answer, callback.from_user.id)
    await callback.answer()
