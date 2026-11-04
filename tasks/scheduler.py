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
        
        # СЛОЖНЫЙ РАСЧЕТ БИЗНЕСОВ
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sql_biz = f"""
            UPDATE players 
            SET balance = balance + (
                (COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level) +
                (CAST(COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level * 0.2 AS INTEGER) * business_staff) +
                (CASE WHEN business_boost IS NOT NULL AND business_boost > '{now}' THEN CAST(COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level * 0.5 AS INTEGER) ELSE 0 END)
                - (COALESCE((SELECT upkeep FROM businesses WHERE businesses.id = players.business_id), 0) * business_level)
            ) WHERE business_id > 0
        """
        await db.execute(sql_biz)
        await db.execute("UPDATE players SET balance = balance - 5")
        
        # МАЙНИНГ
        sql_btc = "UPDATE players SET crypto_btc = COALESCE(crypto_btc, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 2.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'BTC'"
        await db.execute(sql_btc)
        
        sql_eth = "UPDATE players SET crypto_eth = COALESCE(crypto_eth, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 33.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'ETH'"
        await db.execute(sql_eth)
        
        sql_doge = "UPDATE players SET crypto_doge = COALESCE(crypto_doge, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 10000.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'DOGE'"
        await db.execute(sql_doge)
        
        # Износ деталей
        sql_wear = "UPDATE mining_rigs SET mb_cond = MAX(0, mb_cond - 0.5), psu_cond = MAX(0, psu_cond - 0.5), cpu_cond = MAX(0, cpu_cond - 0.5) WHERE mb_id > 0 OR psu_id > 0 OR cpu_id > 0"
        await db.execute(sql_wear)
        await db.execute("UPDATE mining_rig_gpus SET cond = MAX(0, cond - 0.5)")
        
        await db.execute("UPDATE players SET reputation = MIN(reputation + 1, 100) WHERE job_salary > 0")
        await db.commit()

async def change_season():
    async with aiosqlite.connect(DB_PATH) as db:
        seasons = ["Зима", "Весна", "Лето", "Осень"]
        new_season = random.choice(seasons)
        await db.execute("UPDATE system_state SET value=? WHERE key='season'", (new_season,))
        await db.commit()
        async with db.execute("SELECT user_id FROM players") as cur:
            users = await cur.fetchall()
        for u in users:
            try: await bot.send_message(u[0], f"🍂 **Сменился сезон.** Наступила **{new_season}**.\nЦены на аренду изменились!")
            except: pass

async def random_events():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM players WHERE balance > 0") as cur:
            users = await cur.fetchall()
        if not users: return
        user_id = random.choice(users)[0]
        events = [
            ("good", 500, "💰 Ты нашел на улице кошелек и там было 500 монет!"),
            ("good", 1000, "🎁 Прохожий подарил тебе 1000 монет просто так!"),
            ("bad", -300, "💸 Налоговая нашла ошибку. Штраф: 300 монет."),
            ("bad", -200, "😡 У тебя украли кошелек в толпе. Потеряно 200 монет.")
        ]
        _, amount, text = random.choice(events)
        if amount != 0:
            await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (amount, user_id))
            await db.commit()
        try: await bot.send_message(user_id, f"🎲 **Случайное событие!**\n\n{text}")
        except: pass

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
    scheduler.add_job(random_events, "interval", minutes=15)
    scheduler.add_job(change_season, "interval", hours=24)
    scheduler.start()
