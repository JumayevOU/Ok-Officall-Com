from aiogram.fsm.state import State, StatesGroup
from typing import Optional, Any
import logging

# Logger sozlamalari
logger = logging.getLogger(__name__)

class StateManager:
    """State larni boshqarish klassi"""
    
    @staticmethod
    def validate_state_data(state_data: dict, required_fields: list) -> tuple[bool, str]:
        """
        State ma'lumotlarini tekshirish
        
        Args:
            state_data: State ma'lumotlari
            required_fields: Majburiy maydonlar
        
        Returns:
            tuple: (tekshirish natijasi, xabar)
        """
        try:
            if not state_data:
                return False, "Ma'lumotlar bo'sh"
            
            for field in required_fields:
                if field not in state_data:
                    return False, f"Majburiy maydon yo'q: {field}"
                if not state_data[field]:
                    return False, f"Maydon bo'sh: {field}"
            
            return True, "OK"
        except Exception as e:
            logger.error(f"❌ State ma'lumotlarini tekshirishda xatolik: {e}")
            return False, f"Validatsiya xatosi: {str(e)}"

# --- ISHCHI BOSHQARUHI STATES ---

class AddWorker(StatesGroup):
    """Yangi ishchi qo'shish states"""
    name = State()
    rate = State()
    location = State()
    confirmation = State()  # Tasdiqlash qo'shildi

class EditWorker(StatesGroup):
    """Ishchini tahrirlash states"""
    select_worker = State()
    name = State()
    rate = State()
    location = State()
    confirmation = State()

class ArchiveWorker(StatesGroup):
    """Ishchini arxivlash states"""
    select_worker = State()
    confirmation = State()
    reason = State()  # Sababini kiritish

class RestoreWorker(StatesGroup):
    """Ishchini qayta tiklash states"""
    select_worker = State()
    confirmation = State()

# --- DAVOMAT STATES ---

class DailyReport(StatesGroup):
    """Kunlik hisobot states"""
    entering_hours = State()
    confirmation = State()
    bulk_entry = State()  # Bir nechta ishchi uchun bir vaqtda

class MonthlyReport(StatesGroup):
    """Oylik hisobot states"""
    select_month = State()
    select_year = State()
    confirmation = State()

class EditAttendance(StatesGroup):
    """Davomatni tahrirlash states"""
    select_worker = State()
    select_date = State()
    enter_hours = State()
    confirmation = State()

# --- MOLIYAVIY STATES ---

class AddAdvance(StatesGroup):
    """Avans qo'shish states"""
    worker_select = State()
    amount = State()
    description = State()  # Tavsif qo'shildi
    confirmation = State()

class EditAdvance(StatesGroup):
    """Avansni tahrirlash states"""
    select_advance = State()
    amount = State()
    description = State()
    confirmation = State()

class SalaryCalculation(StatesGroup):
    """Maosh hisoblash states"""
    select_period = State()
    select_workers = State()
    confirmation = State()
    payment_method = State()  # To'lov usuli

class PaymentProcessing(StatesGroup):
    """To'lov amalga oshirish states"""
    select_worker = State()
    amount = State()
    method = State()
    confirmation = State()

# --- KIRISH VA AUTENTIFIKATSIYA STATES ---

class WorkerLogin(StatesGroup):
    """Ishchi kirish states"""
    waiting_code = State()
    verification = State()  # Tasdiqlash
    setup_profile = State()  # Profil sozlash

class AdminLogin(StatesGroup):
    """Admin kirish states"""
    username = State()
    password = State()
    verification = State()

class ChangePassword(StatesGroup):
    """Parol o'zgartirish states"""
    current_password = State()
    new_password = State()
    confirmation = State()

# --- HISOBOT VA EKSPORT STATES ---

class ExcelReport(StatesGroup):
    """Excel hisobot states"""
    report_type = State()
    period_selection = State()
    format_settings = State()
    confirmation = State()

class CustomReport(StatesGroup):
    """Maxsus hisobot states"""
    report_type = State()
    date_range = State()
    workers_selection = State()
    columns_selection = State()
    confirmation = State()

class ExportData(StatesGroup):
    """Ma'lumotlarni eksport qilish states"""
    data_type = State()
    format = State()
    date_range = State()
    confirmation = State()

# --- SOZLAMALAR STATES ---

class SystemSettings(StatesGroup):
    """Tizim sozlamalari states"""
    main_settings = State()
    notification_settings = State()
    backup_settings = State()
    confirmation = State()

class NotificationSettings(StatesGroup):
    """Bildirishnoma sozlamalari states"""
    enable_notifications = State()
    report_time = State()
    advance_alerts = State()
    confirmation = State()

class BackupSettings(StatesGroup):
    """Zaxiralash sozlamalari states"""
    auto_backup = State()
    backup_frequency = State()
    cloud_storage = State()
    confirmation = State()

# --- YORDAM VA QO'LLAB-QUVVATLASH STATES ---

class SupportRequest(StatesGroup):
    """Yordam so'rash states"""
    issue_type = State()
    description = State()
    priority = State()
    confirmation = State()

class Feedback(StatesGroup):
    """Fikr-mulohaza states"""
    rating = State()
    comment = State()
    contact_permission = State()
    confirmation = State()

# --- QO'SHIMCHA FUNKSIYALAR STATES ---

class BulkOperations(StatesGroup):
    """Bir vaqtli operatsiyalar states"""
    operation_type = State()
    workers_selection = State()
    data_entry = State()
    confirmation = State()

class DataImport(StatesGroup):
    """Ma'lumotlarni import qilish states"""
    file_upload = State()
    data_mapping = State()
    validation = State()
    confirmation = State()

class LocationManagement(StatesGroup):
    """Lokatsiyalarni boshqarish states"""
    add_location = State()
    edit_location = State()
    delete_location = State()
    confirmation = State()

# --- STATE YORDAMCHI FUNKSIYALARI ---

def get_state_display_name(state_class: StatesGroup) -> str:
    """State klassining ko'rinadigan nomini olish"""
    state_names = {
        'AddWorker': "Yangi ishchi qo'shish",
        'EditWorker': "Ishchini tahrirlash",
        'DailyReport': "Kunlik hisobot",
        'AddAdvance': "Avans qo'shish",
        'WorkerLogin': "Ishchi kirishi",
        'ExcelReport': "Excel hisobot",
        'SystemSettings': "Tizim sozlamalari",
        'SupportRequest': "Yordam so'rash"
    }
    return state_names.get(state_class.__name__, state_class.__name__)

def get_state_required_fields(state_class: StatesGroup, state: State) -> list:
    """State uchun majburiy maydonlarni olish"""
    requirements = {
        ('AddWorker', 'name'): ['name'],
        ('AddWorker', 'rate'): ['name', 'rate'],
        ('AddWorker', 'location'): ['name', 'rate', 'location'],
        ('AddAdvance', 'worker_select'): ['worker_id'],
        ('AddAdvance', 'amount'): ['worker_id', 'amount'],
        ('DailyReport', 'entering_hours'): ['queue', 'index', 'processed_count'],
    }
    
    key = (state_class.__name__, state.state if hasattr(state, 'state') else str(state))
    return requirements.get(key, [])

def clear_state_data(state_data: dict, preserve_fields: list = None) -> dict:
    """
    State ma'lumotlarini tozalash
    
    Args:
        state_data: State ma'lumotlari
        preserve_fields: Saqlab qolish kerak bo'lgan maydonlar
    
    Returns:
        dict: Tozalangan ma'lumotlar
    """
    try:
        if preserve_fields is None:
            preserve_fields = []
        
        # Faqat saqlash kerak bo'lgan maydonlarni qoldirish
        cleaned_data = {field: state_data[field] for field in preserve_fields if field in state_data}
        
        return cleaned_data
    except Exception as e:
        logger.error(f"❌ State ma'lumotlarini tozalashda xatolik: {e}")
        return {}

def validate_state_transition(current_state: str, next_state: str, allowed_transitions: dict) -> bool:
    """
    State o'tishini tekshirish
    
    Args:
        current_state: Joriy state
        next_state: Keyingi state
        allowed_transitions: Ruxsat etilgan o'tishlar
    
    Returns:
        bool: O'tish ruxsat etilgan yoki yo'q
    """
    try:
        if current_state not in allowed_transitions:
            return False
        
        return next_state in allowed_transitions[current_state]
    except Exception as e:
        logger.error(f"❌ State o'tishini tekshirishda xatolik: {e}")
        return False

# --- STATE KONSTANTALARI ---

# Ruxsat etilgan state o'tishlari
ALLOWED_TRANSITIONS = {
    'AddWorker:name': ['AddWorker:rate'],
    'AddWorker:rate': ['AddWorker:location'],
    'AddWorker:location': ['AddWorker:confirmation'],
    'AddAdvance:worker_select': ['AddAdvance:amount'],
    'AddAdvance:amount': ['AddAdvance:description'],
    'AddAdvance:description': ['AddAdvance:confirmation'],
    'DailyReport:entering_hours': ['DailyReport:confirmation'],
}

# State guruhlari ro'yxati
STATE_GROUPS = [
    AddWorker, EditWorker, ArchiveWorker, RestoreWorker,
    DailyReport, MonthlyReport, EditAttendance,
    AddAdvance, EditAdvance, SalaryCalculation, PaymentProcessing,
    WorkerLogin, AdminLogin, ChangePassword,
    ExcelReport, CustomReport, ExportData,
    SystemSettings, NotificationSettings, BackupSettings,
    SupportRequest, Feedback,
    BulkOperations, DataImport, LocationManagement
]

# State nomlari
STATE_NAMES = {state_class.__name__: state_class for state_class in STATE_GROUPS}

def get_state_class_by_name(name: str) -> Optional[StatesGroup]:
    """Nom bo'yicha state klassini olish"""
    return STATE_NAMES.get(name)

# Export qilinadigan asosiy state guruhlari
__all__ = [
    # Asosiy state guruhlari
    'AddWorker',
    'DailyReport', 
    'AddAdvance',
    'WorkerLogin',
    
    # Yangi qo'shilgan state guruhlari
    'EditWorker',
    'ArchiveWorker',
    'RestoreWorker',
    'MonthlyReport',
    'EditAttendance',
    'EditAdvance',
    'SalaryCalculation',
    'PaymentProcessing',
    'AdminLogin',
    'ChangePassword',
    'ExcelReport',
    'CustomReport',
    'ExportData',
    'SystemSettings',
    'NotificationSettings',
    'BackupSettings',
    'SupportRequest',
    'Feedback',
    'BulkOperations',
    'DataImport',
    'LocationManagement',
    
    # Yordamchi funksiyalar
    'StateManager',
    'get_state_display_name',
    'get_state_required_fields',
    'clear_state_data',
    'validate_state_transition',
    'get_state_class_by_name'
]