import aiosqlite, random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from config import BOT_TOKEN
from database import DB_PATH

scheduler = AsyncIOScheduler()
bot = Bot(token=BOT_TOKEN)

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM system_state WHERE key='season'") as cur:
            season = (await cur.fetchone())[0]
            
        season_mult = 1.0
        if season == "Зима": season_mult = 1.3
        if season == "Весна": season_mult = 0.9
        if season == "Осень": season_mult = 1.1
        
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        await db.execute(f"UPDATE players SET balance = balance - (COALESCE((SELECT rent FROM properties WHERE properties.id = players.property_id), 0) * {season_mult}) WHERE property_id > 0")
        
        # МАССОВЫЙ РАСЧЕТ БИЗНЕСОВ
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(f"""
            UPDATE players 
            SET balance = balance + (
                SELECT COALESCE(SUM(
                    (b.income * pb.level) +
                    (CAST(b.income * pb.level * 0.2 AS INTEGER) * pb.staff) +
                    (CASE WHEN pb.boost IS NOT NULL AND pb.boost > '{now}' THEN CAST(b.income * pb.level * 0.5 AS INTEGER) ELSE 0 END)
                    - (b.upkeep * pb.level)
                ), 0)
                FROM player_businesses pb
                JOIN businesses b ON pb.business_id = b.id
                WHERE pb.user_id = players.user_id
            )
        """)
        
        await db.execute("UPDATE players SET balance = balance - 5")
        
        # Майнинг
        await db.execute("UPDATE players SET crypto_btc = COALESCE(crypto_btc, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 2.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'BTC'")
        await db.execute("UPDATE players SET crypto_eth = COALESCE(crypto_eth, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 33.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'ETH'")
        await db.execute("UPDATE players SET crypto_doge = COALESCE(crypto_doge, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 10000.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'DOGE'")
        
        # Износ деталей
        await db.execute("UPDATE mining_rigs SET mb_cond = MAX(0, mb_cond - 0.5), psu_cond = MAX(0, psu_cond - 0.5), cpu_cond = MAX(0, cpu_cond - 0.5) WHERE mb_id > 0 OR psu_id > 0 OR cpu_id > 0")
        await db.execute("UPDATE mining_rig_gpus SET cond = MAX(0, cond - 0.5)")
        
        await db.execute("UPDATE players SET reputation = MIN(reputation + 1, 100) WHERE job_salary > 0")
        await db.commit()

# (Остальные функции change_season, random_events, update_prices, start_scheduler остаются без изменений)
