import aiosqlite, random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import DB_PATH

scheduler = AsyncIOScheduler()

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        # Зарплата
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        # Аренда
        await db.execute("UPDATE players SET balance = balance - COALESCE((SELECT rent_cost FROM properties WHERE properties.id = players.property_id), 0) WHERE property_id > 0")
        # Бизнесы
        await db.execute("UPDATE players SET balance = balance + (COALESCE((SELECT passive_income FROM businesses WHERE businesses.id = players.business_id), 0) - COALESCE((SELECT upkeep_cost FROM businesses WHERE businesses.id = players.business_id), 0)) WHERE business_id > 0")
        # Еда
        await db.execute("UPDATE players SET balance = balance - 30")
        
        # МАЙНИНГ (начисляем BTC)
        await db.execute("UPDATE players SET crypto_btc = crypto_btc + (mining_rigs * 0.01) WHERE mining_rigs > 0")
        
        await db.commit()

async def update_crypto_prices():
    async with aiosqlite.connect(DB_PATH) as db:
        for table in ["crypto_assets", "stock_assets"]:
            async with db.execute(f"SELECT symbol, price, volatility FROM {table}") as cur:
                assets = await cur.fetchall()
            for a in assets:
                change = a[1] * random.uniform(-a[2], a[2])
                new_price = max(1.0, a[1] + change)
                await db.execute(f"UPDATE {table} SET price=? WHERE symbol=?", (new_price, a[0]))
        await db.commit()

def start_scheduler():
    scheduler.add_job(process_cycle, "interval", minutes=5)
    scheduler.add_job(update_crypto_prices, "interval", minutes=5)
    scheduler.start()
