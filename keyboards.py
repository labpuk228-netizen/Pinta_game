from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
        [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🎓 Образование")],
        [KeyboardButton(text="🏢 Бизнесы"), KeyboardButton(text="📈 Биржа")],
        [KeyboardButton(text="⛏️ Майнинг"), KeyboardButton(text="🤝 Социалка")],
        [KeyboardButton(text="🎲 Казино"), KeyboardButton(text="🕵️ Криминал")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="💸 Перевод")],
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📩 Поддержка")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="🛡 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_players_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад в админку")]], resize_keyboard=True)
def job_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📋 Вакансии"), KeyboardButton(text="🛠 Подработки")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def prop_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Моё жильё"), KeyboardButton(text="🏘 Вся недвижимость")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def biz_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏢 Мои бизнесы"), KeyboardButton(text="💼 Купить бизнес")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def mining_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🖥 Мои фермы"), KeyboardButton(text="🛒 Магазин деталей")],[KeyboardButton(text="💸 Продать детали"), KeyboardButton(text="🪙 Сменить монету")],[KeyboardButton(text="💸 Вывести в портфель")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def market_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📈 Крипта"), KeyboardButton(text="📊 Акции")],[KeyboardButton(text="💼 Портфель"), KeyboardButton(text="📜 Мои ордера")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def social_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏰 Кланы"), KeyboardButton(text="🏦 Банк и Кредиты")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def casino_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="💵 Изменить ставку")],[KeyboardButton(text="🎰 Рулетка"), KeyboardButton(text="🎲 Кости")],[KeyboardButton(text="🎟 Лотерея"), KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
def crime_menu(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛒 Черный рынок"), KeyboardButton(text="🦹 Ограбить игрока")],[KeyboardButton(text="👤 Ограбить NPC"), KeyboardButton(text="💻 Взломать банк")],[KeyboardButton(text="🛡 Купить охрану"), KeyboardButton(text="⚖️ Выйти из тюрьмы")],[KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)
