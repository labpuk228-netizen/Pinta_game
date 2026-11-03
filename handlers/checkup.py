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
    
    # 1. Проверка файла БД
    if os.path.exists(DB_PATH):
        results.append("✅ Файл базы данных найден")
    else:
        results.append("❌ Файл базы данных НЕ найден")
        errors += 1
    
    # 2. Проверка всех таблиц
    required_tables = ["players", "jobs", "properties", "educations", "businesses", "admins"]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for table in required_tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                        count = (await cur.fetchone())[0]
                        results.append(f"✅ Таблица `{table}`: {count} записей")
                except Exception:
                    results.append(f"❌ Таблица `{table}`: ОШИБКА (не создана?)")
                    errors += 1
    except Exception as e:
        results.append(f"❌ Не удалось подключиться к БД: {e}")
        errors += 1
    
    # 3. Проверка колонок в таблице players
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("PRAGMA table_info(players)") as cur:
                columns = [row[1] for row in await cur.fetchall()]
            required_cols = ["user_id", "username", "transfer_code", "balance", "job_salary", 
                             "property_id", "education_level", "business_id", "last_side_job", "last_fortune"]
            missing = [c for c in required_cols if c not in columns]
            if missing:
                results.append(f"❌ Отсутствуют колонки: {', '.join(missing)}")
                errors += 1
            else:
                results.append("✅ Все колонки `players` на месте")
    except Exception as e:
        results.append(f"❌ Ошибка проверки колонок: {e}")
        errors += 1
    
    # 4. Проверка состояния конкретного игрока
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM players WHERE user_id=?", (user_id,)) as cur:
                player = await cur.fetchone()
        if player:
            results.append("✅ Твой профиль найден в БД")
            results.append(f"   💰 Баланс: {player[3]}")
            results.append(f"   💼 Зарплата: {player[4]}")
            results.append(f"   🏠 Жильё ID: {player[7] if len(player) > 7 else '?'}")
            results.append(f"   🎓 Образование: {player[8] if len(player) > 8 else '?'}")
            results.append(f"   🏢 Бизнес ID: {player[9] if len(player) > 9 else '?'}")
            if player[3] < 0:
                results.append("⚠️ Баланс отрицательный! Возможно, расходы больше доходов.")
        else:
            results.append("❌ Твой профиль не найден (нажми /start)")
            errors += 1
    except Exception as e:
        results.append(f"❌ Ошибка проверки игрока: {e}")
        errors += 1
    
    # 5. Проверка планировщика (пассивный доход/расход)
    try:
        if scheduler.running:
            jobs_count = len(scheduler.get_jobs())
            results.append(f"✅ Планировщик работает ({jobs_count} задач)")
        else:
            results.append("❌ Планировщик НЕ запущен")
            errors += 1
    except Exception as e:
        results.append(f"❌ Ошибка планировщика: {e}")
        errors += 1
    
    # 6. Проверка переменных окружения
    if os.environ.get("BOT_TOKEN"):
        results.append("✅ BOT_TOKEN задан")
    else:
        results.append("❌ BOT_TOKEN НЕ задан")
        errors += 1
    
    if os.environ.get("ADMIN_ID"):
        results.append(f"✅ ADMIN_ID = {os.environ.get('ADMIN_ID')}")
    else:
        results.append("⚠️ ADMIN_ID не задан")
    
    # Итог
    if errors == 0:
        results.append("\n🎉 **Все тесты пройдены успешно!**")
    else:
        results.append(f"\n⚠️ **Найдено проблем: {errors}**")
    
    text = "🧪 **Результаты тестирования:**\n\n" + "\n".join(results)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Дать 10000 монет (тест)", callback_data="dev_give_money")],
        [InlineKeyboardButton(text="⚙️ Прогнать пассивный цикл", callback_data="dev_run_cycle")],
        [InlineKeyboardButton(text="🔄 Перезапустить тест", callback_data="dev_rerun")]
    ])
    
    # Telegram ограничивает сообщения 4096 символами
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
        await callback.answer("✅ Пассивный цикл выполнен! Проверь баланс в профиле.", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка цикла: {e}", show_alert=True)


@router.callback_query(F.data == "dev_rerun")
async def rerun_test(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await _test_core(callback.message.answer, callback.from_user.id)
    await callback.answer()
