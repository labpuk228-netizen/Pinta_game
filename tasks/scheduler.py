import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import DB_PATH

scheduler = AsyncIOScheduler()

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Начисляем зарплату
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        
        # 2. Списываем аренду жилья (если оно съемное и есть property_id)
        await db.execute("""
            UPDATE players 
            SET balance = balance - COALESCE((SELECT rent_cost FROM properties WHERE properties.id = players.property_id), 0)
            WHERE property_id > 0
        """)
        
        # 3. Базовые расходы на еду и воду (например, 30 монет за цикл)
        await db.execute("UPDATE players SET balance = balance - 30")
        
        await db.commit()

def start_scheduler():
    # Для теста оставляем 1 минуту. Позже поменяем на 1 час.
    scheduler.add_job(process_cycle, "interval", minutes=1)
    scheduler.start()
