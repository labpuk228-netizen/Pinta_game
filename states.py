from aiogram.fsm.state import State, StatesGroup

class TransferState(StatesGroup):
    waiting_code = State()
    waiting_amount = State()

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_balance = State()
    waiting_property = State()
    waiting_business = State()
    waiting_ban_reason = State()

class MarketState(StatesGroup):
    waiting_order_amount = State()
    waiting_order_price = State()

class SocialState(StatesGroup):
    waiting_clan_name = State()
    waiting_loan_amount = State()
