from aiogram.fsm.state import State, StatesGroup

class AddWorker(StatesGroup):
    name = State()
    rate = State()
    location = State()

class EditWorker(StatesGroup):
    waiting_id = State()
    waiting_field = State()
    waiting_value = State()

class DeleteWorker(StatesGroup):
    waiting_id = State()

class DailyReport(StatesGroup):
    enter_hours = State()

class AdminAdvance(StatesGroup):
    select_worker = State()
    enter_amount = State()

class WorkerAdvance(StatesGroup):
    enter_amount = State()

class WorkerLogin(StatesGroup):
    enter_code = State()