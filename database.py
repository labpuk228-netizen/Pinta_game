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
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        """)

        # РАСШИРЕННЫЙ СПИСОК ОБРАЗОВАНИЯ (Уровни 1-4)
        edus = [
            (1, 'Курсы IT (Базовые)', 2000, 1), 
            (2, 'Курсы Электрика', 2000, 1),
            (3, 'Курсы Медицины (Медбрат)', 3000, 1),
            (4, 'Высшее IT (Программист)', 15000, 2),
            (5, 'Высшее Экономическое', 15000, 2),
            (6, 'Высшее Медицинское (Врач)', 25000, 3),
            (7, 'Высшее Инженерное', 20000, 3),
            (8, 'MBA (Бизнес)', 50000, 3),
            (9, 'Аспирантура / PhD', 100000, 4)
        ]
        for e in edus: await db.execute("INSERT OR REPLACE INTO educations VALUES (?,?,?,?)", e)

        # РАСШИРЕННЫЙ СПИСОК РАБОТ (Привязаны к образованию и жилью)
        jobs = [
            # Базовые (без требований)
            (1, 'Курьер', 20, 0, 0), (2, 'Грузчик', 15, 0, 0), 
            (3, 'Официант', 18, 0, 0), (4, 'Таксист', 25, 0, 0),
            # Требуют Ур.1
            (5, 'Сантехник', 45, 1, 1), (6, 'Электрик', 50, 1, 1), 
            (7, 'Медбрат', 60, 1, 1),
            # Требуют Ур.2
            (8, 'Программист', 150, 2, 2), (9, 'Дизайнер', 120, 2, 2), 
            (10, 'Бухгалтер', 100, 2, 2),
            # Требуют Ур.3
            (11, 'Топ-менеджер', 400, 3, 3), (12, 'Врач', 450, 3, 3), 
            (13, 'Инженер', 350, 3, 3), (14, 'Финансовый аналитик', 500, 3, 3),
            # Требуют Ур.4 (Элита)
            (15, 'Главврач', 1000, 4, 5), (16, 'Финансовый директор', 1200, 4, 5),
            (17, 'Крипто-трейдер', 1500, 4, 5)
        ]
        for j in jobs: await db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?)", j)

        # 15 ВИДОВ ПОДРАБОТОК
        sj = [
            (1, "Раздача листовок", 5, 15, 2, 0, 0), 
            (2, "Помощь соседям", 8, 20, 3, 0, 0),
            (3, "Выгул собак", 10, 25, 2, 0, 0),
            (4, "Мытье машин", 15, 40, 4, 0, 0),
            (5, "Курьер на час", 15, 35, 4, 0, 0),
            (6, "Расклейка объявлений", 12, 30, 3, 0, 0),
            (7, "Помощь в магазине", 30, 60, 5, 1, 0),
            (8, "Ремонт телефонов", 40, 80, 6, 1, 0),
            (9, "Репетиторство", 60, 120, 8, 2, 0),
            (10, "Ремонт техники", 50, 100, 7, 2, 1),
            (11, "Фриланс-дизайн", 80, 150, 8, 2, 2),
            (12, "Фриланс-программирование", 120, 250, 10, 2, 2),
            (13, "Бизнес-консалтинг", 200, 400, 12, 3, 3),
            (14, "Инвест-аналитика", 350, 700, 15, 3, 4),
            (15, "Аудит безопасности", 500, 1000, 20, 4, 5)
        ]
        for s in sj: await db.execute("INSERT OR REPLACE INTO side_jobs VALUES (?,?,?,?,?,?,?)", s)

        # Жилье и Бизнесы (оставляем как было)
        props = [
            (0, 'На улице', 0, 0, 0), (1, 'Общага', 10, 1000, 1), (2, 'Студия', 30, 5000, 2),
            (3, 'Однушка', 50, 10000, 2), (4, 'Двушка', 80, 20000, 3), (5, 'Трёшка', 120, 35000, 3),
            (6, 'Дом', 200, 70000, 4), (7, 'Коттедж', 400, 150000, 4), (8, 'Пентхаус', 1000, 500000, 5),
            (9, 'Особняк', 2000, 1500000, 5), (10, 'Остров', 10000, 10000000, 6)
        ]
        for p in props: await db.execute("INSERT OR REPLACE INTO properties VALUES (?,?,?,?,?)", p)
        
        bizs = [
            (1, 'Ларёк с шаурмой', 5000, 200, 50), (2, 'Кофейня', 15000, 600, 150),
            (3, 'Автомойка', 30000, 1200, 300), (4, 'Барбершоп', 50000, 2000, 500),
            (5, 'Ресторан', 120000, 5000, 1200), (6, 'Отель', 300000, 12000, 3000),
            (7, 'IT-Стартап', 500000, 25000, 6000), (8, 'Завод', 1000000, 60000, 15000),
            (9, 'Банк', 5000000, 300000, 80000), (10, 'Медиахолдинг', 10000000, 600000, 150000)
        ]
        for b in bizs: await db.execute("INSERT OR REPLACE INTO businesses VALUES (?,?,?,?,?)", b)

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
