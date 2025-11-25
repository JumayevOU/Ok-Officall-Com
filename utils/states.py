from aiogram.fsm.state import State, StatesGroup

class AddWorker(StatesGroup):
    name = State()
    rate = State()

class DailyReport(StatesGroup):
    entering_hours = State() # Sikl uchun

class AddAdvance(StatesGroup):
    worker_id = State()
    amount = State()

class WorkerLogin(StatesGroup):
    waiting_code = State()