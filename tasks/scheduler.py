import aiosqlite, random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import DB_PATH

scheduler = AsyncIOScheduler()

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Зарплаты
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        
        # 2. Аренда жилья (если не куплено)
        await db.execute("UPDATE players SET balance = balance - COALESCE((SELECT rent FROM properties WHERE properties.id = players.property_id), 0) WHERE property_id > 0")
        
        # 3. Бизнесы (доход минус обслуживание)
        await db.execute("""
            UPDATE players 
            SET balance = balance + (
                COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level - 
                COALESCE((SELECT upkeep FROM businesses WHERE businesses.id = players.business_id), 0) * business_level
            )
            WHERE business_id > 0
        """)
        
        # 4. Еда и вода (базовый расход - 5 монет)
        await db.execute("UPDATE players SET balance = balance - 5")
        
        await db.commit()

def start_scheduler():
    scheduler.add_job(process_cycle, "interval", minutes=5)
    scheduler.start()
