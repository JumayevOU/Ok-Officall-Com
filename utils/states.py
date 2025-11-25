from aiogram.fsm.state import State, StatesGroup

class AddWorker(StatesGroup):
    name = State()
    rate = State()
    location = State()

class DailyReport(StatesGroup):
    entering_hours = State()

class AddAdvance(StatesGroup):
    worker_select = State()
    amount = State()

class WorkerLogin(StatesGroup):
    waiting_code = State()