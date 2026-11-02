from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🎓 Образование")],
            [KeyboardButton(text="💸 Перевод"), KeyboardButton(text="🏆 Топ игроков")]
        ],
        resize_keyboard=True
    )
