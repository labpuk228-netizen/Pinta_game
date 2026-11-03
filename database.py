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
            last_fortune TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            salary INTEGER,
            required_education INTEGER DEFAULT 0,
            required_property INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            rent_cost INTEGER,
            buy_cost INTEGER
        );
        CREATE TABLE IF NOT EXISTS educations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            cost INTEGER,
            level INTEGER
        );
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            buy_cost INTEGER,
            passive_income INTEGER,
            upkeep_cost INTEGER
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        );
        """)
        
        # Миграция (добавляем колонки, если их нет)
        columns = [
            "property_id INTEGER DEFAULT 0", 
            "education_level INTEGER DEFAULT 0", 
            "business_id INTEGER DEFAULT 0",
            "last_side_job TIMESTAMP",
            "last_fortune TIMESTAMP"
        ]
        for col in columns:
            try:
                await db.execute(f"ALTER TABLE players ADD COLUMN {col}")
            except aiosqlite.OperationalError:
                pass

        try:
            await db.execute("ALTER TABLE jobs ADD COLUMN required_property INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            pass

        # Базовые работы
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (1, 'Курьер', 200, 0, 0)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (2, 'Грузчик', 150, 0, 0)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (3, 'Сантехник', 450, 1, 1)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (4, 'Программист', 1200, 1, 2)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary, required_education, required_property) VALUES (5, 'Топ-менеджер', 3500, 2, 3)")
        
        # Базовое жилье
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (0, 'На улице', 0, 0)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (1, 'Общага', 50, 1000)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (2, 'Студия', 150, 5000)")
        await db.execute("INSERT OR IGNORE INTO properties (id, title, rent_cost, buy_cost) VALUES (3, 'Дом', 500, 25000)")
        
        # Базовое образование
        await db.execute("INSERT OR IGNORE INTO educations (id, title, cost, level) VALUES (1, 'Курсы IT', 2000, 1)")
        await db.execute("INSERT OR IGNORE INTO educations (id, title, cost, level) VALUES (2, 'Высшее образование', 10000, 2)")

        # Базовые бизнесы
        await db.execute("INSERT OR IGNORE INTO businesses (id, title, buy_cost, passive_income, upkeep_cost) VALUES (1, 'Кофейня', 10000, 500, 100)")
        await db.execute("INSERT OR IGNORE INTO businesses (id, title, buy_cost, passive_income, upkeep_cost) VALUES (2, 'Автомойка', 25000, 1200, 200)")

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
        await db.execute(
            "INSERT OR IGNORE INTO players (user_id, username, transfer_code, last_online) VALUES (?,?,?,CURRENT_TIMESTAMP)",
            (user_id, username, code)
        )
        await db.commit()
    return code

async def update_online(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET last_online=CURRENT_TIMESTAMP WHERE user_id=?", (user_id,))
        await db.commit()
