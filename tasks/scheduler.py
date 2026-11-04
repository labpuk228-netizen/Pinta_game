import aiosqlite, random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from database import DB_PATH

scheduler = AsyncIOScheduler()
bot = Bot(token=BOT_TOKEN)

async def process_cycle():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET balance = balance + job_salary WHERE job_salary > 0")
        await db.execute("UPDATE players SET balance = balance - 5")
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(f"""
            UPDATE players 
            SET balance = balance + (
                SELECT COALESCE(SUM(
                    (b.income * pb.level) + (CAST(b.income * pb.level * 0.2 AS INTEGER) * pb.staff) +
                    (CASE WHEN pb.boost IS NOT NULL AND pb.boost > '{now}' THEN CAST(b.income * pb.level * 0.5 AS INTEGER) ELSE 0 END)
                    - (b.upkeep * pb.level)
                ), 0) FROM player_businesses pb JOIN businesses b ON pb.business_id = b.id WHERE pb.user_id = players.user_id
            )
        """)
        
        await db.execute("UPDATE players SET crypto_btc = COALESCE(crypto_btc, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 2.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'BTC'")
        await db.execute("UPDATE players SET crypto_eth = COALESCE(crypto_eth, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 33.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'ETH'")
        await db.execute("UPDATE players SET crypto_doge = COALESCE(crypto_doge, 0) + (SELECT COALESCE(SUM(sp.hashrate * rg.amount * (rg.cond/100.0)), 0) * 10000.0 FROM mining_rig_gpus rg JOIN mining_rigs r ON rg.rig_id = r.id JOIN mining_shop sp ON rg.part_id = sp.id WHERE r.user_id = players.user_id) WHERE mining_coin = 'DOGE'")
        
        await db.execute("UPDATE mining_rigs SET mb_cond = MAX(0, mb_cond - 0.5), psu_cond = MAX(0, psu_cond - 0.5), cpu_cond = MAX(0, cpu_cond - 0.5) WHERE mb_id > 0 OR psu_id > 0 OR cpu_id > 0")
        await db.execute("UPDATE mining_rig_gpus SET cond = MAX(0, cond - 0.5)")
        await db.execute("UPDATE players SET reputation = MIN(reputation + 1, 100) WHERE job_salary > 0")
        await db.commit()

async def npc_events():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, balance FROM players WHERE balance > 1000") as cur:
            users = await cur.fetchall()
        if not users: return
        
        user_id, balance = random.choice(users)
        npcs = ["Алиса", "Барон фон Крипто", "Максим", "Синдикат"]
        npc = random.choice(npcs)
        
        event_type = random.randint(1, 3)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Принять", callback_data=f"npc_yes_{event_type}"), InlineKeyboardButton(text="❌ Отказать", callback_data="npc_no")]])
        
        if event_type == 1:
            text = f"💼 Тебе пишет **{npc}**:\n«Привет! Я вижу, ты неплохо устроился. Одолжи мне 5000 монет до завтра? Верну 6000.»"
        elif event_type == 2:
            text = f"📈 Тебе пишет **{npc}**:\n«Слышал, BTC скоро взлетит. Дам тебе инсайд за 1000 монет. Купишь?»"
        else:
            text = f"🥊 Тебе пишет **{npc}**:\n«Слабо заработать 2000 монет за 5 минут? Если успеешь, я дам тебе 4000. Спорим?»"
            
        try: await bot.send_message(user_id, text, reply_markup=kb, parse_mode="Markdown")
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
    scheduler.add_job(npc_events, "interval", minutes=20) # НПС пишут раз в 20 минут
    scheduler.start()
