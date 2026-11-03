from aiogram import Router, F
from aiogram.types import Message
from keyboards import main_menu

router = Router()

@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_menu())

def paginate(items, page, per_page=5):
    start = page * per_page
    end = start + per_page
    return items[start:end], len(items) > end

def page_nav_buttons(prefix, page, has_next):
    from aiogram.types import InlineKeyboardButton
    btns = []
    if page > 0:
        btns.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}_page_{page-1}"))
    if has_next:
        btns.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"{prefix}_page_{page+1}"))
    return btns
