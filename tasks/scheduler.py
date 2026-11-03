from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def process_cycle():
    pass # Здесь будет экономика (5 минут)

def start_scheduler():
    scheduler.add_job(process_cycle, "interval", minutes=5)
    scheduler.start()
