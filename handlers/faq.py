from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import section_menu

router = Router()

@router.message(F.text == "❓ FAQ")
async def show_faq(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 С чего начать?", callback_data="faq_start")],
        [InlineKeyboardButton(text="💰 Как заработать?", callback_data="faq_money")],
        [InlineKeyboardButton(text="📈 Биржа и крипта", callback_data="faq_market")],
        [InlineKeyboardButton(text="⛏️ Майнинг", callback_data="faq_mining")],
        [InlineKeyboardButton(text="🤝 Социалка", callback_data="faq_social")]
    ])
    await message.answer("📖 **FAQ**\n\nВыбери раздел:", parse_mode="Markdown", reply_markup=kb)
    await message.answer("Навигация:", reply_markup=section_menu())

@router.callback_query(F.data.startswith("faq_"))
async def faq_section(callback: CallbackQuery):
    texts = {
        "faq_start": "🚀 **С чего начать?**\n1. Нажми 💼 Работа — устройся курьером.\n2. Подрабатывай (кнопка 🛠).\n3. Купи 🎓 образование.\n4. Сними 🏠 жильё.",
        "faq_money": "💰 **Как заработать?**\nРаботы, подработки, бизнесы, биржа, майнинг, фортуна.",
        "faq_market": "📈 **Биржа**\nПокупай BTC/ETH/акции дешевле — продавай дороже. Курс меняется каждые 5 минут.",
        "faq_mining": "⛏️ **Майнинг**\nКупи оборудование (видеокарты), собирай ферму. Доход зависит от мощности и курса BTC.",
        "faq_social": "🤝 **Социалка**\nКланы (5000 монет), кредиты в банке, переводы другим игрокам по коду."
    }
    await callback.message.edit_text(texts.get(callback.data, "В разработке"), parse_mode="Markdown")
    await callback.answer()
