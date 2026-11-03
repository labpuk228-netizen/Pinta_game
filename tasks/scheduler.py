import aiosqlite, random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import DB_PATH

scheduler = AsyncIOScheduler()

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        await db.execute("UPDATE players SET balance = balance - COALESCE((SELECT rent FROM properties WHERE properties.id = players.property_id), 0) WHERE property_id > 0")
        await db.execute("""
            UPDATE players 
            SET balance = balance + (
                COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level - 
                COALESCE((SELECT upkeep FROM businesses WHERE businesses.id = players.business_id), 0) * business_level
            ) WHERE business_id > 0
        """)
        await db.execute("UPDATE players SET balance = balance - 50")
        
        # МАЙНИНГ (Дробные части)
        await db.execute("""
            UPDATE players SET crypto_btc = COALESCE(crypto_btc, 0) + (
                SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 0.001 
                FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id
            ) WHERE mining_coin = 'BTC'
        """)
        await db.execute("""
            UPDATE players SET crypto_eth = COALESCE(crypto_eth, 0) + (
                SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 0.01 
                FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id
            ) WHERE mining_coin = 'ETH'
        """)
        await db.execute("""
            UPDATE players SET crypto_doge = COALESCE(crypto_doge, 0) + (
                SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 0.5 
                FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id
            ) WHERE mining_coin = 'DOGE'
        """)
        await db.commit()

async def update_prices():
    async with aiosqlite.connect(DB_PATH) as db:
        for table in ["crypto_assets", "stock_assets"]:
            async with db.execute(f"SELECT symbol, price, volatility FROM {table}") as cur:
                assets = await cur.fetchall()
            for a in assets:
                change = a[1] * random.uniform(-a[2], a[2])
                new_price = max(0.01, a[1] + change)
                await db.execute(f"UPDATE {table} SET price=? WHERE symbol=?", (new_price, a[0]))
        await db.commit()

def start_scheduler():
    scheduler.add_job(process_cycle, "interval", minutes=5)
    scheduler.add_job(update_prices, "interval", minutes=5)
    scheduler.start()
