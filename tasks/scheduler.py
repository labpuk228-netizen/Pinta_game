import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import DB_PATH

scheduler = AsyncIOScheduler()


async def pay_salaries():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        await db.commit()


def start_scheduler():
    scheduler.add_job(pay_salaries, "interval", minutes=1)
    scheduler.start()
