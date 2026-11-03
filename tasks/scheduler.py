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
        await db.execute("UPDATE players SET balance = balance + (COALESCE((SELECT income FROM businesses WHERE businesses.id = players.business_id), 0) * business_level - COALESCE((SELECT upkeep FROM businesses WHERE businesses.id = players.business_id), 0) * business_level) WHERE business_id > 0")
        await db.execute("UPDATE players SET balance = balance - 5")
        
        await db.execute("UPDATE players SET crypto_btc = COALESCE(crypto_btc, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 2.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'BTC'")
        await db.execute("UPDATE players SET crypto_eth = COALESCE(crypto_eth, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 33.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'ETH'")
        await db.execute("UPDATE players SET crypto_doge = COALESCE(crypto_doge, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount), 0) * 10000.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'DOGE'")
        
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
            try: await bot.send_message(u[0], f"🍂 **Внимание! Сменился сезон.**\nНаступила **{new_season}**.\n\nЦены на аренду могут измениться!")
            except: pass

async def random_events():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, mining_coin FROM players WHERE balance > 0") as cur:
            users = await cur.fetchall()
        if not users: return
        user_id, mining_coin = random.choice(users)
        events = [
            ("good", 500, "💰 Ты нашел на улице кошелек и там было 500 монет!"),
            ("good", 1000, "🎁 Прохожий подарил тебе 1000 монет просто так!"),
            ("good", 200, "🍀 Ты сорвал джекпот в уличной лотерее: 200 монет!"),
            ("bad", -300, "💸 Налоговая нашла ошибку в твоих бумагах. Штраф: 300 монет."),
            ("bad", -200, "😡 У тебя украли кошелек в толпе. Потеряно 200 монет."),
            ("bad", 0, "⚡ У тебя скачок напряжения! Оборудование отключилось (пропущен цикл).")
        ]
        event_type, amount, text = random.choice(events)
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
