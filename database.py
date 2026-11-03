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
        
        -- Таблица подработок с новой колонкой no_cooldown_edu
        CREATE TABLE IF NOT EXISTS side_jobs (
            id INTEGER PRIMARY KEY, title TEXT, min_e INTEGER, max_e INTEGER, 
            cooldown INTEGER, req_edu INTEGER, req_prop INTEGER, no_cooldown_edu INTEGER DEFAULT 99
        );
        
        CREATE TABLE IF NOT EXISTS side_cooldowns (user_id INTEGER, job_id INTEGER, last_done TIMESTAMP, PRIMARY KEY (user_id, job_id));
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        """)

        # Миграция для тех у кого БД уже создана
        try: await db.execute("ALTER TABLE side_jobs ADD COLUMN no_cooldown_edu INTEGER DEFAULT 99")
        except aiosqlite.OperationalError: pass

        # 6 УРОВНЕЙ ОБРАЗОВАНИЯ
        edus = [
            (1, 'Курсы IT (Базовые)', 2000, 1), 
            (2, 'Курсы Электрика', 2000, 1),
            (3, 'Медицинский колледж', 3000, 1),
            (4, 'Высшее IT (Бакалавр)', 15000, 2),
            (5, 'Высшее Экономическое', 15000, 2),
            (6, 'Высшее Медицинское', 25000, 3),
            (7, 'Высшее Инженерное', 20000, 3),
            (8, 'Магистратура', 40000, 4),
            (9, 'MBA (Бизнес)', 80000, 4),
            (10, 'Аспирантура', 150000, 5),
            (11, 'Докторантура / PhD', 300000, 6)
        ]
        for e in edus: await db.execute("INSERT OR REPLACE INTO educations VALUES (?,?,?,?)", e)

        # РАБОТЫ
        jobs = [
            (1, 'Курьер', 20, 0, 0), (2, 'Грузчик', 15, 0, 0), (3, 'Официант', 18, 0, 0), (4, 'Таксист', 25, 0, 0),
            (5, 'Сантехник', 45, 1, 1), (6, 'Электрик', 50, 1, 1), (7, 'Медбрат', 60, 1, 1), (8, 'Техподдержка', 55, 1, 1),
            (9, 'Программист (Junior)', 150, 2, 2), (10, 'Дизайнер', 120, 2, 2), (11, 'Бухгалтер', 100, 2, 2),
            (12, 'Программист (Middle)', 300, 3, 2), (13, 'Врач-терапевт', 350, 3, 3), (14, 'Инженер-проектировщик', 320, 3, 3),
            (15, 'Программист (Senior)', 600, 4, 3), (16, 'Финансовый аналитик', 700, 4, 4), (17, 'Хирург', 800, 4, 4),
            (18, 'Топ-менеджер', 1500, 5, 5), (19, 'Главврач', 1800, 5, 5),
            (20, 'Генеральный директор (CEO)', 4000, 6, 6)
        ]
        for j in jobs: await db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?)", j)

        # ПОДРАБОТКИ (id, title, min, max, cooldown, req_edu, req_prop, no_cd_edu)
        sj = [
            # Базовые (кулдаун пропадает на 2 ур.)
            (1, "Раздача листовок", 5, 15, 2, 0, 0, 2), 
            (2, "Помощь соседям", 8, 20, 3, 0, 0, 2),
            (3, "Выгул собак", 10, 25, 2, 0, 0, 2),
            (4, "Мытье машин", 15, 40, 4, 0, 0, 2),
            (5, "Курьер на час", 15, 35, 4, 1, 0, 3),
            (6, "Помощь в магазине", 30, 60, 5, 1, 0, 3),
            (7, "Ремонт телефонов", 40, 80, 6, 1, 0, 3),
            # Средние (кулдаун пропадает на 3-4 ур.)
            (8, "Репетиторство", 60, 120, 8, 2, 0, 4),
            (9, "Ремонт техники", 50, 100, 7, 2, 1, 4),
            (10, "Фриланс-дизайн", 80, 150, 8, 2, 2, 4),
            (11, "Фриланс-программирование", 120, 250, 10, 2, 2, 4),
            # Высокие (кулдаун пропадает на 5 ур.)
            (12, "Написание статей на заказ", 150, 300, 10, 3, 2, 5),
            (13, "Бизнес-консалтинг", 200, 400, 12, 3, 3, 5),
            (14, "Инвест-аналитика", 350, 700, 15, 4, 4, 5),
            (15, "Аудит безопасности", 400, 800, 15, 4, 4, 5),
            (16, "Разработка на заказ (Срочно)", 500, 1000, 20, 4, 3, 5),
            # Элитные (кулдаун пропадает на 6 ур.)
            (17, "Оценка стартапов", 800, 1600, 20, 5, 5, 6),
            (18, "Консультация для корпораций", 1200, 2500, 30, 5, 5, 6),
            (19, "Чтение лекций", 2000, 4000, 30, 6, 0, 99), # У лекций всегда есть перерыв
            (20, "Стратегический советник", 3000, 6000, 40, 6, 6, 99)
        ]
        for s in sj: await db.execute("INSERT OR REPLACE INTO side_jobs VALUES (?,?,?,?,?,?,?,?)", s)

        # Жилье и Бизнесы
        props = [(0, 'На улице', 0, 0, 0), (1, 'Общага', 10, 1000, 1), (2, 'Студия', 30, 5000, 2), (3, 'Однушка', 50, 10000, 2), (4, 'Двушка', 80, 20000, 3), (5, 'Трёшка', 120, 35000, 3), (6, 'Дом', 200, 70000, 4), (7, 'Коттедж', 400, 150000, 4), (8, 'Пентхаус', 1000, 500000, 5), (9, 'Особняк', 2000, 1500000, 5), (10, 'Остров', 10000, 10000000, 6)]
        for p in props: await db.execute("INSERT OR REPLACE INTO properties VALUES (?,?,?,?,?)", p)
        
        bizs = [(1, 'Ларёк с шаурмой', 5000, 200, 50), (2, 'Кофейня', 15000, 600, 150), (3, 'Автомойка', 30000, 1200, 300), (4, 'Барбершоп', 50000, 2000, 500), (5, 'Ресторан', 120000, 5000, 1200), (6, 'Отель', 300000, 12000, 3000), (7, 'IT-Стартап', 500000, 25000, 6000), (8, 'Завод', 1000000, 60000, 15000), (9, 'Банк', 5000000, 300000, 80000), (10, 'Медиахолдинг', 10000000, 600000, 150000)]
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
