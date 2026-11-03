import aiosqlite
import random
import string
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
            last_side_job TIMESTAMP, last_fortune TIMESTAMP, last_crime TIMESTAMP,
            clan_id INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 100, in_prison_until TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT, salary INTEGER, req_edu INTEGER, req_prop INTEGER);
        CREATE TABLE IF NOT EXISTS properties (id INTEGER PRIMARY KEY, title TEXT, rent INTEGER, buy INTEGER, comfort INTEGER);
        CREATE TABLE IF NOT EXISTS educations (id INTEGER PRIMARY KEY, title TEXT, cost INTEGER, level INTEGER);
        CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY, title TEXT, buy INTEGER, income INTEGER, upkeep INTEGER);
        
        CREATE TABLE IF NOT EXISTS side_jobs (id INTEGER PRIMARY KEY, title TEXT, min_e INTEGER, max_e INTEGER, cooldown INTEGER, req_edu INTEGER, req_prop INTEGER);
        CREATE TABLE IF NOT EXISTS side_cooldowns (user_id INTEGER, job_id INTEGER, last_done TIMESTAMP, PRIMARY KEY (user_id, job_id));
        
        CREATE TABLE IF NOT EXISTS mining_shop (id INTEGER PRIMARY KEY, part_type TEXT, name TEXT, price INTEGER, hashrate REAL, wattage INTEGER, slots INTEGER);
        CREATE TABLE IF NOT EXISTS mining_inventory (user_id INTEGER, part_id INTEGER, amount INTEGER DEFAULT 1, PRIMARY KEY (user_id, part_id));
        CREATE TABLE IF NOT EXISTS mining_rigs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, mb_id INTEGER DEFAULT 0, psu_id INTEGER DEFAULT 0, cpu_id INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS mining_rig_gpus (rig_id INTEGER, part_id INTEGER, amount INTEGER DEFAULT 1, PRIMARY KEY (rig_id, part_id));
        
        CREATE TABLE IF NOT EXISTS crypto_assets (symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL);
        CREATE TABLE IF NOT EXISTS stock_assets (symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL);
        CREATE TABLE IF NOT EXISTS market_portfolio (user_id INTEGER, symbol TEXT, amount REAL DEFAULT 0, PRIMARY KEY (user_id, symbol));
        CREATE TABLE IF NOT EXISTS market_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, symbol TEXT, amount REAL, target_price REAL, status TEXT DEFAULT 'active');
        
        CREATE TABLE IF NOT EXISTS clans (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, leader_id INTEGER, bank INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS loans (id INTEGER PRIMARY KEY AUTOINCREMENT, lender_id INTEGER, borrower_id INTEGER, amount INTEGER, percent INTEGER, due_date TIMESTAMP, status TEXT DEFAULT 'active');
        
        CREATE TABLE IF NOT EXISTS npcs (id INTEGER PRIMARY KEY, name TEXT, balance INTEGER, behavior TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        """)
        
        # Базовые работы
        jobs = [
            (1, 'Курьер', 20, 0, 0), (2, 'Грузчик', 15, 0, 0), (3, 'Официант', 18, 0, 0),
            (4, 'Сантехник', 45, 1, 1), (5, 'Электрик', 50, 1, 1), (6, 'Программист', 120, 1, 2),
            (7, 'Дизайнер', 90, 1, 2), (8, 'Топ-менеджер', 350, 2, 3), (9, 'Врач', 400, 2, 3),
            (10, 'Аналитик', 450, 3, 4)
        ]
        for j in jobs: await db.execute("INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?)", j)
        
        # Жилье
        props = [
            (0, 'На улице', 0, 0, 0), (1, 'Общага', 10, 1000, 1), (2, 'Студия', 30, 5000, 2),
            (3, 'Однушка', 50, 10000, 2), (4, 'Двушка', 80, 20000, 3), (5, 'Трёшка', 120, 35000, 3),
            (6, 'Дом', 200, 70000, 4), (7, 'Коттедж', 400, 150000, 4), (8, 'Пентхаус', 1000, 500000, 5),
            (9, 'Особняк', 2000, 1500000, 5), (10, 'Остров', 10000, 10000000, 6)
        ]
        for p in props: await db.execute("INSERT OR IGNORE INTO properties VALUES (?,?,?,?,?)", p)
        
        # Образование
        edus = [
            (1, 'Курсы IT', 2000, 1), (2, 'Курсы Электрика', 2000, 1), 
            (3, 'Высшее образование', 10000, 2), (4, 'MBA', 50000, 3)
        ]
        for e in edus: await db.execute("INSERT OR IGNORE INTO educations VALUES (?,?,?,?)", e)
        
        # Бизнесы
        bizs = [
            (1, 'Ларёк с шаурмой', 5000, 200, 50), (2, 'Кофейня', 15000, 600, 150),
            (3, 'Автомойка', 30000, 1200, 300), (4, 'Барбершоп', 50000, 2000, 500),
            (5, 'Ресторан', 120000, 5000, 1200), (6, 'Отель', 300000, 12000, 3000),
            (7, 'IT-Стартап', 500000, 25000, 6000), (8, 'Завод', 1000000, 60000, 15000),
            (9, 'Банк', 5000000, 300000, 80000), (10, 'Медиахолдинг', 10000000, 600000, 150000)
        ]
        for b in bizs: await db.execute("INSERT OR IGNORE INTO businesses VALUES (?,?,?,?,?)", b)
        
        # Подработки
        sj = [
            (1, "Раздача листовок", 5, 15, 2, 0, 0), (2, "Помощь соседям", 8, 20, 3, 0, 0),
            (3, "Курьер на час", 15, 35, 4, 0, 0), (4, "Помощь в магазине", 30, 60, 5, 1, 0),
            (5, "Ремонт техники", 50, 100, 7, 1, 1), (6, "Фриланс-программирование", 80, 150, 10, 1, 2),
            (7, "Бизнес-консалтинг", 150, 300, 10, 2, 3), (8, "Инвест-аналитика", 300, 600, 15, 3, 4)
        ]
        for s in sj: await db.execute("INSERT OR IGNORE INTO side_jobs VALUES (?,?,?,?,?,?,?)", s)

        # Комплектующие для майнинга (type: case, mb, psu, cpu, gpu)
        parts = [
            (1, 'case', 'Дешевый корпус (2 слота)', 1000, 0, 0, 2), (2, 'case', 'Средний риг (4 слота)', 5000, 0, 0, 4), (3, 'case', 'Промышленная стойка (8 слотов)', 20000, 0, 0, 8),
            (4, 'mb', 'Материнка Mini (2 слота)', 500, 0, 50, 2), (5, 'mb', 'Материнка ATX (4 слота)', 2500, 0, 100, 4), (6, 'mb', 'Материнка PRO (8 слотов)', 10000, 0, 200, 8),
            (7, 'psu', 'БП 500W', 800, 0, 500, 0), (8, 'psu', 'БП 1000W', 3000, 0, 1000, 0), (9, 'psu', 'БП 2000W', 12000, 0, 2000, 0),
            (10, 'cpu', 'Celeron', 1000, 0.005, 30, 0), (11, 'cpu', 'Ryzen 5', 5000, 0.02, 65, 0), (12, 'cpu', 'Threadripper', 25000, 0.1, 150, 0),
            (13, 'gpu', 'GTX 1050', 3000, 0.01, 75, 0), (14, 'gpu', 'RTX 3060', 15000, 0.05, 170, 0), (15, 'gpu', 'RTX 4090', 80000, 0.25, 450, 0)
        ]
        for p in parts: await db.execute("INSERT OR IGNORE INTO mining_shop VALUES (?,?,?,?,?,?,?)", p)

        # Биржа
        crypto = [('BTC', 'Bitcoin', 500.0, 0.05), ('ETH', 'Ethereum', 50.0, 0.08), ('DOGE', 'Doge', 0.1, 0.15)]
        for c in crypto: await db.execute("INSERT OR IGNORE INTO crypto_assets VALUES (?,?,?,?)", c)
        stocks = [('PINTA', 'Pinta Corp', 100.0, 0.03), ('TECH', 'TechnoSoft', 250.0, 0.06)]
        for s in stocks: await db.execute("INSERT OR IGNORE INTO stock_assets VALUES (?,?,?,?)", s)

        if ADMIN_ID:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
            await db.execute("UPDATE players SET is_admin=1 WHERE user_id=?", (ADMIN_ID,))
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
