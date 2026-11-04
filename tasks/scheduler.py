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
        
        # СЛОЖНЫЙ РАСЧЕТ БИЗНЕСОВ (С УЧЕТОМ СОТРУДНИКОВ И БУСТА)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(f"""
            UPDATE players 
            SET balance = balance + (
                (COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level) +
                (CAST(COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level * 0.2 AS INTEGER) * business_staff) +
                (CASE WHEN business_boost IS NOT NULL AND business_boost > '{now}' THEN CAST(COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level * 0.5 AS INTEGER) ELSE 0 END)
                - (COALESCE((SELECT upkeep FROM businesses WHERE businesses.id = players.business_id), 0) * business_level)
            ) WHERE business_id > 0
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

# ... (функции change_season, random_events, update_prices и start_scheduler остаются без изменений, они уже есть в твоем файле)
