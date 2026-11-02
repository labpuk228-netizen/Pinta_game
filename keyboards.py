from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="💸 Перевод")],
        ],
        resize_keyboard=True
    )
