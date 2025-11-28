from aiogram.fsm.state import State, StatesGroup

class AddWorker(StatesGroup):
    name = State()
    rate = State()
    location = State()

class DeleteWorker(StatesGroup):
    waiting_id = State()

class EditWorker(StatesGroup):
    waiting_id = State()
    waiting_field = State()
    waiting_value = State()

class DailyReport(StatesGroup):
    entering_hours = State()

class AddAdvance(StatesGroup):
    worker_select = State()
    amount = State()

class RequestAdvance(StatesGroup):
    amount = State()

class WorkerLogin(StatesGroup):
    waiting_code = State()

class SetLocation(StatesGroup):
    waiting_loc = State()