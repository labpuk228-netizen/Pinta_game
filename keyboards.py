from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🎓 Образование")],
            [KeyboardButton(text="🏢 Бизнесы"), KeyboardButton(text="🎲 Фортуна")],
            [KeyboardButton(text="💸 Перевод"), KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(text="🧪 Тест (Dev)")]
        ],
        resize_keyboard=True
    )
