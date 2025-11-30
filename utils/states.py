from aiogram.fsm.state import State, StatesGroup

class AddWorker(StatesGroup):
    name = State()
    rate = State()
    location = State()

class EditWorker(StatesGroup):
    select_worker = State()
    select_field = State()
    enter_value = State()

class DeleteWorker(StatesGroup):
    select_worker = State()
    confirmation = State()

class DailyReport(StatesGroup):
    enter_hours = State()

class AdminAdvance(StatesGroup):
    select_worker = State()
    enter_amount = State()

class WorkerAdvance(StatesGroup):
    enter_amount = State()
    confirmation = State()

class WorkerLogin(StatesGroup):
    enter_code = State()

class Broadcast(StatesGroup):
    enter_message = State()
    confirmation = State()