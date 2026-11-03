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
    
    if os.path.exists(DB_PATH):
        results.append("✅ Файл базы данных найден")
    else:
        results.append("❌ Файл базы данных НЕ найден")
        errors += 1
    
    required_tables = ["players", "jobs", "properties", "educations", "businesses", "side_jobs", "side_jobs_cooldown", "crypto_assets", "stock_assets", "clans", "loans", "admins"]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for table in required_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                        count = (await cur.fetchone())[0]
                        results.append(f"✅ Таблица `{table}`: {count} записей")
                except Exception:
                    results.append(f"❌ Таблица `{table}`: ОШИБКА")
                    errors += 1
    except Exception as e:
        results.append(f"❌ Не удалось подключиться к БД: {e}")
        errors += 1
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("PRAGMA table_info(players)") as cur:
                columns = [row[1] for row in await cur.fetchall()]
            required_cols = ["user_id", "balance", "job_salary", "property_id", "education_level", 
                             "business_id", "clan_id", "mining_rigs", "crypto_btc", "crypto_eth"]
            missing = [c for c in required_cols if c not in columns]
            if missing:
                results.append(f"❌ Отсутствуют колонки: {', '.join(missing)}")
                errors += 1
            else:
                results.append("✅ Все колонки `players` на месте")
    except Exception as e:
        results.append(f"❌ Ошибка колонок: {e}")
        errors += 1
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM players WHERE user_id=?", (user_id,)) as cur:
                player = await cur.fetchone()
        if player:
            results.append("✅ Твой профиль найден")
            results.append(f"   💰 Баланс: {player[3]}")
            results.append(f"   🏠 Жильё ID: {player[6]}")
            results.append(f"   🎓 Образование: {player[7]}")
            results.append(f"   ⛏️ Фермы: {player[12]}")
            results.append(f"   🪙 BTC: {player[13]:.4f}")
        else:
            results.append("❌ Профиль не найден (нажми /start)")
            errors += 1
    except Exception as e:
        results.append(f"❌ Ошибка игрока: {e}")
        errors += 1
    
    if scheduler.running: results.append("✅ Планировщик работает")
    else: results.append("❌ Планировщик не запущен"); errors += 1
    
    if errors == 0: results.append("\n🎉 **Все тесты пройдены!**")
    else: results.append(f"\n⚠️ **Найдено проблем: {errors}**")
    
    text = "🧪 **Тестирование системы:**\n\n" + "\n".join(results)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Дать 10000 монет (тест)", callback_data="dev_give_money")],
        [InlineKeyboardButton(text="⚙️ Прогнать пассивный цикл", callback_data="dev_run_cycle")],
        [InlineKeyboardButton(text="🔄 Перезапустить тест", callback_data="dev_rerun")]
    ])
    
    await respond_func(text[:4000], parse_mode="Markdown", reply_markup=keyboard)

@router.message(F.text == "🧪 Тест (Dev)")
async def run_tests(message: Message):
    await _test_core(message.answer, message.from_user.id)

@router.callback_query(F.data == "dev_give_money")
async def give_money(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + 10000 WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.answer("💵 Начислено 10000 тестовых монет!", show_alert=True)

@router.callback_query(F.data == "dev_run_cycle")
async def run_cycle(callback: CallbackQuery):
    try:
        await process_cycle()
        await callback.answer("✅ Пассивный цикл выполнен! (Зарплата, налоги, майнинг)", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "dev_rerun")
async def rerun_test(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await _test_core(callback.message.answer, callback.from_user.id)
    await callback.answer()
