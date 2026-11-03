from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🎓 Образование")],
            [KeyboardButton(text="🏢 Бизнесы"), KeyboardButton(text="📈 Биржа")],
            [KeyboardButton(text="⛏️ Майнинг"), KeyboardButton(text="🤝 Социалка")],
            [KeyboardButton(text="🎲 Фортуна"), KeyboardButton(text="🏆 Топ")],
            [KeyboardButton(text="💸 Перевод"), KeyboardButton(text="❓ FAQ")]
        ],
        resize_keyboard=True
    )

def section_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад в меню")]],
        resize_keyboard=True
    )
