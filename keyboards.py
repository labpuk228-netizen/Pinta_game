from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
        [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🎓 Образование")],
        [KeyboardButton(text="🏢 Бизнесы"), KeyboardButton(text="📈 Биржа")],
        [KeyboardButton(text="⛏️ Майнинг"), KeyboardButton(text="🤝 Социалка")],
        [KeyboardButton(text="🎲 Казино"), KeyboardButton(text="🕵️ Криминал")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="💸 Перевод")],
        [KeyboardButton(text="❓ FAQ")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="🛡 Админ-панель"), KeyboardButton(text="🧪 Тест")])
    else:
        kb.append([KeyboardButton(text="🧪 Тест")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def mining_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🖥 Мои фермы"), KeyboardButton(text="🛒 Магазин деталей")],
        [KeyboardButton(text="🪙 Сменить монету"), KeyboardButton(text="💸 Вывести в портфель")], # НОВАЯ КНОПКА
        [KeyboardButton(text="⬅️ Назад в меню")]
    ], resize_keyboard=True)

def casino_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💵 Изменить ставку")],
        [KeyboardButton(text="🎰 Рулетка"), KeyboardButton(text="🎲 Кости")],
        [KeyboardButton(text="🎟 Лотерея"), KeyboardButton(text="⬅️ Назад в меню")]
    ], resize_keyboard=True)

def crime_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Черный рынок"), KeyboardButton(text="🦹 Ограбить игрока")],
        [KeyboardButton(text="👤 Ограбить NPC"), KeyboardButton(text="💻 Взломать банк")],
        [KeyboardButton(text="🛡 Купить охрану"), KeyboardButton(text="⚖️ Выйти из тюрьмы")],
        [KeyboardButton(text="⬅️ Назад в меню")]
    ], resize_keyboard=True)

def job_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📋 Вакансии"), KeyboardButton(text="🛠 Подработки")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def prop_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Моё жильё"), KeyboardButton(text="🏘 Вся недвижимость")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def biz_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏢 Мои бизнесы"), KeyboardButton(text="💼 Купить бизнес")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def market_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📈 Крипта"), KeyboardButton(text="📊 Акции")],[KeyboardButton(text="💼 Портфель"), KeyboardButton(text="📜 Мои ордера")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def social_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏰 Кланы"), KeyboardButton(text="🏦 Банк и Кредиты")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def admin_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Игроки")],[KeyboardButton(text="💰 Экономика"), KeyboardButton(text="🌍 Мир и Ивенты")],[KeyboardButton(text="⚙️ Система"), KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
