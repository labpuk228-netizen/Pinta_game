import aiosqlite
import random
import string
from datetime import datetime
from config import ADMIN_ID

DB_PATH = "economy.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY, username TEXT, transfer_code TEXT UNIQUE,
            balance INTEGER DEFAULT 1000, job_salary INTEGER DEFAULT 0, job_stage INTEGER DEFAULT 0,
            last_online TIMESTAMP DEFAULT CURRENT_TIMESTAMP, property_id INTEGER DEFAULT 0,
            education_level INTEGER DEFAULT 0, business_id INTEGER DEFAULT 0, business_level INTEGER DEFAULT 1,
            business_staff INTEGER DEFAULT 0, business_boost TIMESTAMP,
            last_side_job TIMESTAMP, last_fortune TIMESTAMP, last_crime TIMESTAMP,
            clan_id INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 100, in_prison_until TIMESTAMP,
            crypto_btc REAL DEFAULT 0, crypto_eth REAL DEFAULT 0, stock_pinta REAL DEFAULT 0,
            mining_coin TEXT DEFAULT 'BTC', crypto_doge REAL DEFAULT 0, has_security INTEGER DEFAULT 0,
            has_lockpicks INTEGER DEFAULT 0, has_hacker_software INTEGER DEFAULT 0, current_bet INTEGER DEFAULT 100
        );
        CREATE TABLE IF NOT EXISTS player_businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, business_id INTEGER,
            level INTEGER DEFAULT 1, staff INTEGER DEFAULT 0, boost TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'open'
        );
        CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT, salary INTEGER, req_edu INTEGER, req_prop INTEGER);
        CREATE TABLE IF NOT EXISTS properties (id INTEGER PRIMARY KEY, title TEXT, rent INTEGER, buy INTEGER, comfort INTEGER);
        CREATE TABLE IF NOT EXISTS educations (id INTEGER PRIMARY KEY, title TEXT, cost INTEGER, level INTEGER);
        CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY, title TEXT, buy INTEGER, income INTEGER, upkeep INTEGER);
        CREATE TABLE IF NOT EXISTS side_jobs (id INTEGER PRIMARY KEY, title TEXT, min_e INTEGER, max_e INTEGER, cooldown INTEGER, req_edu INTEGER, req_prop INTEGER, no_cooldown_edu INTEGER DEFAULT 99);
        CREATE TABLE IF NOT EXISTS side_cooldowns (user_id INTEGER, job_id INTEGER, last_done TIMESTAMP, PRIMARY KEY (user_id, job_id));
        CREATE TABLE IF NOT EXISTS mining_shop (id INTEGER PRIMARY KEY, part_type TEXT, name TEXT, price INTEGER, hashrate REAL, wattage INTEGER, slots INTEGER);
        CREATE TABLE IF NOT EXISTS mining_inventory (user_id INTEGER, part_id INTEGER, amount INTEGER DEFAULT 1, cond REAL DEFAULT 100.0, PRIMARY KEY (user_id, part_id));
        CREATE TABLE IF NOT EXISTS mining_rigs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, mb_id INTEGER DEFAULT 0, psu_id INTEGER DEFAULT 0, cpu_id INTEGER DEFAULT 0, mb_cond REAL DEFAULT 100.0, psu_cond REAL DEFAULT 100.0, cpu_cond REAL DEFAULT 100.0);
        CREATE TABLE IF NOT EXISTS mining_rig_gpus (rig_id INTEGER, part_id INTEGER, amount INTEGER DEFAULT 1, cond REAL DEFAULT 100.0, PRIMARY KEY (rig_id, part_id));
        CREATE TABLE IF NOT EXISTS crypto_assets (symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL);
        CREATE TABLE IF NOT EXISTS stock_assets (symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL);
        CREATE TABLE IF NOT EXISTS market_portfolio (user_id INTEGER, symbol TEXT, amount REAL DEFAULT 0, PRIMARY KEY (user_id, symbol));
        CREATE TABLE IF NOT EXISTS market_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, symbol TEXT, amount REAL, target_price REAL, status TEXT DEFAULT 'active');
        CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        """)
        
        try: await db.execute("ALTER TABLE players ADD COLUMN is_banned INTEGER DEFAULT 0")
        except: pass

        if ADMIN_ID:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
            await db.execute("UPDATE players SET is_admin=1 WHERE user_id=?", (ADMIN_ID,))

        # Заполняем базу, если пусто
        async with db.execute("SELECT COUNT(*) FROM jobs") as cur:
            if (await cur.fetchone())[0] == 0:
                edus = [(1, 'Курсы IT', 2000, 1), (2, 'Высшее', 15000, 2), (3, 'MBA', 80000, 3)]
                for e in edus: await db.execute("INSERT INTO educations VALUES (?,?,?,?)", e)
                
                jobs = [(1, 'Курьер', 200, 0, 0), (2, 'Программист', 1500, 2, 2), (3, 'Топ-менеджер', 15000, 5, 5)]
                for j in jobs: await db.execute("INSERT INTO jobs VALUES (?,?,?,?,?)", j)
                
                sj = [(1, "Листовки", 5, 15, 2, 0, 0, 2), (2, "Ремонт", 50, 100, 7, 2, 1, 4)]
                for s in sj: await db.execute("INSERT INTO side_jobs VALUES (?,?,?,?,?,?,?,?)", s)
                
                props = [(0, 'Улица', 0, 0, 0), (1, 'Общага', 10, 1000, 1), (2, 'Студия', 30, 5000, 2)]
                for p in props: await db.execute("INSERT INTO properties VALUES (?,?,?,?,?)", p)
                
                # ВОЗВРАЩАЕМ БИЗНЕСЫ
                bizs = [(1, 'Ларёк', 5000, 200, 50), (2, 'Кофейня', 15000, 600, 150), (3, 'Автомойка', 30000, 1200, 300), (4, 'Ресторан', 120000, 5000, 1200), (5, 'Завод', 1000000, 60000, 15000)]
                for b in bizs: await db.execute("INSERT INTO businesses VALUES (?,?,?,?,?)", b)
                
                parts = [(1, 'case', 'Корпус', 1000, 0, 0, 2), (4, 'mb', 'Мать', 500, 0, 50, 2), (7, 'psu', 'БП', 800, 0, 500, 0), (10, 'cpu', 'Проц', 1000, 0.005, 30, 0), (13, 'gpu', 'Видюха', 3000, 0.01, 75, 0)]
                for p in parts: await db.execute("INSERT INTO mining_shop VALUES (?,?,?,?,?,?,?)", p)

                crypto = [('BTC', 'Bitcoin', 5000.0, 0.05), ('ETH', 'Ethereum', 300.0, 0.08)]
                for c in crypto: await db.execute("INSERT INTO crypto_assets VALUES (?,?,?,?)", c)
                stocks = [('PINTA', 'Pinta Corp', 100.0, 0.03)]
                for s in stocks: await db.execute("INSERT INTO stock_assets VALUES (?,?,?,?)", s)

        await db.commit()

def generate_transfer_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def get_player(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM players WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def create_player(user_id, username):
    code = generate_transfer_code()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO players (user_id, username, transfer_code) VALUES (?,?,?)", (user_id, username, code))
        await db.commit()
    return code

async def is_in_prison(user_id):
    player = await get_player(user_id)
    if player and len(player) > 20 and player[20] and player[20] != "None":
        try:
            prison_time = datetime.strptime(player[20], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() < prison_time:
                rem = prison_time - datetime.utcnow()
                return True, int(rem.total_seconds() // 60)
        except: pass
    return False, 0
