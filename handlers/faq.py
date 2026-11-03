from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.message(F.text.contains("FAQ"))
async def show_faq(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 С чего начать?", callback_data="faq_start")],
        [InlineKeyboardButton(text="💰 Как заработать?", callback_data="faq_money")],
        [InlineKeyboardButton(text="📈 Биржа и крипта", callback_data="faq_market")],
        [InlineKeyboardButton(text="⛏️ Майнинг", callback_data="faq_mining")],
        [InlineKeyboardButton(text="🕵️ Криминал", callback_data="faq_crime")]
    ])
    await message.answer("📖 **Справочный центр**\n\nВыбери раздел, чтобы узнать подробнее:", parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data.startswith("faq_"))
async def faq_section(callback: CallbackQuery):
    texts = {
        "faq_start": "🚀 **С чего начать?**\n1. Нажми 💼 Работа — устройся курьером.\n2. Подрабатывай (кнопка 🛠).\n3. Купи 🎓 образование.\n4. Сними 🏠 жильё.\n5. Попробуй 🎲 Фортуну или Казино.",
        "faq_money": "💰 **Как заработать?**\n- Работа и подработки.\n- Бизнесы (пассивный доход).\n- Майнинг (пассивный доход в крипте).\n- Биржа (покупка дешево, продажа дорого).",
        "faq_market": "📈 **Биржа**\nКурс меняется каждые 5 минут. Покупай BTC/ETH/акции дешевле — продавай дороже. Можно ставить лимитные ордера.",
        "faq_mining": "⛏️ **Майнинг**\nКупи корпус, материнку, БП и видеокарты. Собери ферму в разделе «Мои фермы». Следи за Ваттами! Выбери монету для майнинга.",
        "faq_crime": "🕵️ **Криминал**\nПокупай отмычки на Черном рынке. Граби игроков и NPC. Риск: попасть в тюрьму на 15 минут и потерять репутацию."
    }
    try:
        await callback.message.edit_text(texts.get(callback.data, "В разработке"), parse_mode="Markdown")
    except:
        await callback.message.answer(texts.get(callback.data, "В разработке"), parse_mode="Markdown")
    await callback.answer()
