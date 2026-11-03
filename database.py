import aiosqlite
import random
import string
from config import ADMIN_ID

DB_PATH = "economy.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            transfer_code TEXT UNIQUE,
            balance INTEGER DEFAULT 1000,
            job_salary INTEGER DEFAULT 0,
            last_online TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            property_id INTEGER DEFAULT 0,
            education_level INTEGER DEFAULT 0,
            business_id INTEGER DEFAULT 0,
            last_side_job TIMESTAMP,
            last_fortune TIMESTAMP,
            clan_id INTEGER DEFAULT 0,
            mining_rigs INTEGER DEFAULT 0,
            crypto_btc REAL DEFAULT 0,
            crypto_eth REAL DEFAULT 0,
            stock_pinta REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, salary INTEGER,
            required_education INTEGER DEFAULT 0, required_property INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, rent_cost INTEGER, buy_cost INTEGER
        );
        CREATE TABLE IF NOT EXISTS educations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, cost INTEGER, level INTEGER
        );
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, buy_cost INTEGER, passive_income INTEGER, upkeep_cost INTEGER
        );
        CREATE TABLE IF NOT EXISTS side_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, min_earning INTEGER, max_earning INTEGER,
            cooldown_minutes INTEGER DEFAULT 5,
            required_education INTEGER DEFAULT 0, required_property INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS side_jobs_cooldown (
            user_id INTEGER, side_job_id INTEGER, last_done TIMESTAMP,
            PRIMARY KEY (user_id, side_job_id)
        );
        CREATE TABLE IF NOT EXISTS crypto_assets (
            symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL
        );
        CREATE TABLE IF NOT EXISTS stock_assets (
            symbol TEXT PRIMARY KEY, name TEXT, price REAL, volatility REAL
        );
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, leader_id INTEGER, bank INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lender_id INTEGER, borrower_id INTEGER,
            amount INTEGER, percent INTEGER, status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        """)
        
        # Миграции
        columns = [
            "property_id INTEGER DEFAULT 0", "education_level INTEGER DEFAULT 0", 
            "business_id INTEGER DEFAULT 0", "last_side_job TIMESTAMP", "last_fortune TIMESTAMP",
            "clan_id INTEGER DEFAULT 0", "mining_rigs INTEGER DEFAULT 0",
            "crypto_btc REAL DEFAULT 0", "crypto_eth REAL DEFAULT 0", "stock_pinta REAL DEFAULT 0"
        ]
        for col in columns:
            try: await db.execute(f"ALTER TABLE players ADD COLUMN {col}")
            except aiosqlite.OperationalError: pass

        # Начальные данные
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (1, 'Курьер', 200, 0, 0)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (2, 'Грузчик', 150, 0, 0)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (3, 'Сантехник', 450, 1, 1)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (4, 'Программист', 1200, 1, 2)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (5, 'Топ-менеджер', 3500, 2, 3)")
        
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (0, 'На улице', 0, 0)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (1, 'Общага', 50, 1000)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (2, 'Студия', 150, 5000)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (3, 'Дом', 500, 25000)")
        
        await db.execute("INSERT OR IGNORE INTO educations (id, title, cost, level) VALUES (1, 'Курсы IT', 2000, 1)")
        await db.execute("INSERT OR IGNORE INTO educations (id, title, cost, level) VALUES (2, 'Высшее образование', 10000, 2)")
        
        await db.execute("INSERT OR IGNORE INTO businesses (id, title, buy_cost, passive_income, upkeep_cost) VALUES (1, 'Кофейня', 10000, 500, 100)")
        await db.execute("INSERT OR IGNORE INTO businesses (id, title, buy_cost, passive_income, upkeep_cost) VALUES (2, 'Автомойка', 25000, 1200, 200)")

        side_jobs = [
            (1, "Раздача листовок", 30, 80, 2, 0, 0), (2, "Помощь соседям", 50, 120, 3, 0, 0),
            (3, "Расклейка объявлений", 80, 150, 3, 0, 0), (4, "Курьер на час", 100, 200, 4, 0, 0),
            (5, "Помощь в магазине", 200, 350, 5, 1, 0), (6, "Ремонт техники", 300, 500, 7, 1, 1),
            (7, "Фриланс-программирование", 500, 900, 10, 1, 1), (8, "Бизнес-консалтинг", 800, 1500, 10, 2, 2),
            (9, "Инвестиционная аналитика", 1500, 3000, 15, 2, 3),
        ]
        for sj in side_jobs:
            await db.execute("INSERT OR IGNORE INTO side_jobs (id, title, min_earning, max_earning, cooldown_minutes, required_education, required_property) VALUES (?, ?, ?, ?, ?, ?, ?)", sj)

        await db.execute("INSERT OR IGNORE INTO crypto_assets (symbol, name, price, volatility) VALUES ('BTC', 'Bitcoin', 50000, 0.05)")
        await db.execute("INSERT OR IGNORE INTO crypto_assets (symbol, name, price, volatility) VALUES ('ETH', 'Ethereum', 3000, 0.07)")
        await db.execute("INSERT OR IGNORE INTO stock_assets (symbol, name, price, volatility) VALUES ('PINTA', 'Pinta Corp', 100, 0.03)")
        await db.execute("INSERT OR IGNORE INTO stock_assets (symbol, name, price, volatility) VALUES ('TECH', 'TechnoSoft', 500, 0.04)")

        if ADMIN_ID:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
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
        await db.execute("INSERT OR IGNORE INTO players (user_id, username, transfer_code, last_online) VALUES (?,?,?,CURRENT_TIMESTAMP)", (user_id, username, code))
        await db.commit()
    return code

async def update_online(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET last_online=CURRENT_TIMESTAMP WHERE user_id=?", (user_id,))
        await db.commit()
