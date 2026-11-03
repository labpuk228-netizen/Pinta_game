from aiogram.fsm.state import State, StatesGroup

class TransferState(StatesGroup):
    waiting_code = State()
    waiting_amount = State()

class TradeState(StatesGroup):
    waiting_amount = State()

class OrderState(StatesGroup):
    waiting_amount = State()
    waiting_price = State()
