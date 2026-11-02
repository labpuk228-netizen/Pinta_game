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
            last_online TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            salary INTEGER
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        );
        """)
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary) VALUES (1, 'Курьер', 200)")
        await db.execute("INSERT OR IGNORE INTO jobs (id, title, salary) VALUES (2, 'Грузчик', 150)")
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
