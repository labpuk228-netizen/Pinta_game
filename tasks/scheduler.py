import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import DB_PATH

scheduler = AsyncIOScheduler()

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Начисляем зарплату
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        
        # 2. Списываем аренду жилья
        await db.execute("""
            UPDATE players 
            SET balance = balance - COALESCE((SELECT rent_cost FROM properties WHERE properties.id = players.property_id), 0)
            WHERE property_id > 0
        """)
        
        # 3. Доход от бизнеса минус расходы на него
        await db.execute("""
            UPDATE players 
            SET balance = balance + (
                COALESCE((SELECT passive_income FROM businesses WHERE businesses.id = players.business_id), 0) - 
                COALESCE((SELECT upkeep_cost FROM businesses WHERE businesses.id = players.business_id), 0)
            )
            WHERE business_id > 0
        """)
        
        # 4. Базовые расходы на еду и воду (30 монет)
        await db.execute("UPDATE players SET balance = balance - 30")
        
        await db.commit()

def start_scheduler():
    scheduler.add_job(process_cycle, "interval", minutes=1)
    scheduler.start()
