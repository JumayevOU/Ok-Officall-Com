import calendar
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# Logger sozlamalari
logger = logging.getLogger(__name__)

class ExcelStyles:
    """Excel stil konstantalari"""
    HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    SUBHEADER_FILL = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    LOCATION_FILL = PatternFill(start_color="FCD5B4", end_color="FCD5B4", fill_type="solid")
    WEEKEND_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    HEADER_FONT = Font(bold=True, name='Arial', size=10, color="FFFFFF")
    NORMAL_FONT = Font(name='Arial', size=9)
    BOLD_FONT = Font(bold=True, name='Arial', size=9)
    
    CENTER = Alignment(horizontal="center", vertical="center")
    LEFT = Alignment(horizontal="left", vertical="center")
    RIGHT = Alignment(horizontal="right", vertical="center")
    
    BORDER = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'), 
        bottom=Side(style='thin')
    )

class AdvancedExcelGenerator:
    """Kengaytirilgan Excel hisobot generatori"""
    
    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.num_days = calendar.monthrange(year, month)[1]
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = f"Hisobot {month:02d}.{year}"
        
        # Ma'lumotlar
        self.workers_data = []
        self.attendance_data = {}
        self.advances_data = {}
        
        # Excel parametrlari
        self.current_row = 1
        self.name_col = 1
        self.first_day_col = 2
        self.calc_start_col = self.first_day_col + self.num_days
        
    def validate_input_data(self) -> Tuple[bool, str]:
        """Kirish ma'lumotlarini tekshirish"""
        if not self.workers_data:
            return False, "Ishchilar ma'lumotlari bo'sh"
        
        if not isinstance(self.attendance_data, dict):
            return False, "Davomat ma'lumotlari noto'g'ri formatda"
        
        if not isinstance(self.advances_data, dict):
            return False, "Avans ma'lumotlari noto'g'ri formatda"
        
        return True, "OK"
    
    def setup_column_widths(self):
        """Ustun kengliklarini sozlash"""
        try:
            # Ism ustuni
            self.ws.column_dimensions['A'].width = 25
            
            # Kunlar uchun ustunlar
            for day in range(1, self.num_days + 1):
                col_letter = get_column_letter(self.first_day_col + day - 1)
                self.ws.column_dimensions[col_letter].width = 4
            
            # Hisoblash ustunlari
            calc_columns = ["Soatlik", "Jami Soat", "Avans", "Maosh", "Qoldiq"]
            for i in range(len(calc_columns)):
                col_letter = get_column_letter(self.calc_start_col + i)
                self.ws.column_dimensions[col_letter].width = 10
                
        except Exception as e:
            logger.error(f"❌ Ustun kengliklarini sozlashda xatolik: {e}")
    
    def create_main_header(self):
        """Asosiy sarlavha yaratish"""
        try:
            # Asosiy sarlavha
            end_col = self.calc_start_col + 4
            self.ws.merge_cells(
                start_row=self.current_row, 
                start_column=1, 
                end_row=self.current_row, 
                end_column=end_col
            )
            
            title_cell = self.ws.cell(
                row=self.current_row, 
                column=1, 
                value=f"ISHCHILAR DAVOMATI - {self.month:02d}/{self.year}"
            )
            title_cell.font = Font(bold=True, name='Arial', size=14, color="000000")
            title_cell.alignment = ExcelStyles.CENTER
            title_cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            
            self.current_row += 2
            
        except Exception as e:
            logger.error(f"❌ Asosiy sarlavha yaratishda xatolik: {e}")
            raise
    
    def create_dates_header(self):
        """Sanalar sarlavhasini yaratish"""
        try:
            # Ism uchun bosh joy
            cell = self.ws.cell(row=self.current_row, column=self.name_col, value="F.I.O")
            cell.font = ExcelStyles.HEADER_FONT
            cell.alignment = ExcelStyles.CENTER
            cell.fill = ExcelStyles.HEADER_FILL
            cell.border = ExcelStyles.BORDER
            
            # Sanalar
            for day in range(1, self.num_days + 1):
                col_idx = self.first_day_col + day - 1
                date_obj = datetime(self.year, self.month, day)
                date_str = date_obj.strftime("%d.%m")
                
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=date_str)
                cell.font = ExcelStyles.HEADER_FONT
                cell.alignment = ExcelStyles.CENTER
                cell.fill = ExcelStyles.HEADER_FILL
                cell.border = ExcelStyles.BORDER
                
                # Dam olish kunlari uchun fon
                if date_obj.weekday() >= 5:  # 5=Shanba, 6=Yakshanba
                    cell.fill = ExcelStyles.WEEKEND_FILL
            
            # Hisoblash ustunlari sarlavhalari
            calc_headers = ["Soatlik", "Jami Soat", "Avans", "Maosh", "Qoldiq"]
            for i, header in enumerate(calc_headers):
                col_idx = self.calc_start_col + i
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=header)
                cell.font = ExcelStyles.HEADER_FONT
                cell.alignment = ExcelStyles.CENTER
                cell.fill = ExcelStyles.HEADER_FILL
                cell.border = ExcelStyles.BORDER
            
            self.current_row += 1
            
        except Exception as e:
            logger.error(f"❌ Sanalar sarlavhasini yaratishda xatolik: {e}")
            raise
    
    def group_workers_by_location(self) -> Dict[str, List[Dict]]:
        """Ishchilarni lokatsiya bo'yicha guruhlash"""
        grouped = {}
        for worker in self.workers_data:
            loc = worker.get('location', 'Noma\'lum')
            if loc not in grouped:
                grouped[loc] = []
            grouped[loc].append(worker)
        return grouped
    
    def create_location_section(self, location: str, workers: List[Dict]):
        """Lokatsiya bo'limini yaratish"""
        try:
            # Lokatsiya sarlavhasi
            end_col = self.calc_start_col + 4
            self.ws.merge_cells(
                start_row=self.current_row, 
                start_column=1, 
                end_row=self.current_row, 
                end_column=end_col
            )
            
            location_cell = self.ws.cell(row=self.current_row, column=1, value=f"{location}")
            location_cell.font = ExcelStyles.BOLD_FONT
            location_cell.alignment = ExcelStyles.CENTER
            location_cell.fill = ExcelStyles.LOCATION_FILL
            
            # Border qo'shish
            for col in range(1, end_col + 1):
                self.ws.cell(row=self.current_row, column=col).border = ExcelStyles.BORDER
            
            self.current_row += 1
            
            # Ishchilar ma'lumotlari
            for worker in workers:
                self.add_worker_row(worker)
            
        except Exception as e:
            logger.error(f"❌ Lokatsiya bo'limini yaratishda xatolik: {e}")
            raise
    
    def add_worker_row(self, worker: Dict[str, Any]):
        """Ishchi qatorini qo'shish"""
        try:
            # Ism-familiya
            name_cell = self.ws.cell(row=self.current_row, column=self.name_col, value=worker['name'])
            name_cell.font = ExcelStyles.NORMAL_FONT
            name_cell.alignment = ExcelStyles.LEFT
            name_cell.border = ExcelStyles.BORDER
            
            total_hours = 0
            work_days = 0
            
            # Har bir kun uchun davomat
            for day in range(1, self.num_days + 1):
                col_idx = self.first_day_col + day - 1
                date_key = f"{self.year}-{self.month:02d}-{day:02d}"
                hours = self.attendance_data.get((worker['id'], date_key), 0)
                
                cell = self.ws.cell(row=self.current_row, column=col_idx)
                cell.border = ExcelStyles.BORDER
                cell.alignment = ExcelStyles.CENTER
                cell.font = ExcelStyles.NORMAL_FONT
                
                if hours > 0:
                    cell.value = hours
                    total_hours += hours
                    work_days += 1
                else:
                    cell.value = ""
            
            # Hisob-kitoblar
            rate = worker.get('rate', 0)
            advance = self.advances_data.get(worker['id'], 0)
            total_salary = total_hours * rate
            net_salary = total_salary - advance
            
            # Hisoblash ustunlari
            calc_data = [
                (rate, ExcelStyles.RIGHT),
                (total_hours, ExcelStyles.CENTER),
                (advance, ExcelStyles.RIGHT),
                (total_salary, ExcelStyles.RIGHT),
                (net_salary, ExcelStyles.RIGHT)
            ]
            
            for i, (value, alignment) in enumerate(calc_data):
                col_idx = self.calc_start_col + i
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=value)
                cell.border = ExcelStyles.BORDER
                cell.alignment = alignment
                cell.font = ExcelStyles.NORMAL_FONT
                
                # Format raqamlar
                if isinstance(value, (int, float)):
                    cell.number_format = '#,##0'
            
            # Qoldiq ustunini qalin qilish
            net_cell = self.ws.cell(row=self.current_row, column=self.calc_start_col + 4)
            net_cell.font = ExcelStyles.BOLD_FONT
            
            # Agar qoldiq manfiy bo'lsa, qizil rang
            if net_salary < 0:
                net_cell.fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
            
            self.current_row += 1
            
        except Exception as e:
            logger.error(f"❌ Ishchi qatorini qo'shishda xatolik: {e}")
            raise
    
    def create_summary_section(self):
        """Yakuniy yig'indi bo'limini yaratish"""
        try:
            # Bo'sh qator
            self.current_row += 1
            
            # Yig'indi sarlavhasi
            end_col = self.calc_start_col + 4
            self.ws.merge_cells(
                start_row=self.current_row, 
                start_column=1, 
                end_row=self.current_row, 
                end_column=end_col
            )
            
            summary_cell = self.ws.cell(row=self.current_row, column=1, value="UMUMIY YIG'INDI")
            summary_cell.font = ExcelStyles.BOLD_FONT
            summary_cell.alignment = ExcelStyles.CENTER
            summary_cell.fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
            
            for col in range(1, end_col + 1):
                self.ws.cell(row=self.current_row, column=col).border = ExcelStyles.BORDER
            
            self.current_row += 1
            
            # Yig'indi ma'lumotlari
            total_workers = len(self.workers_data)
            total_hours = 0
            total_advance = 0
            total_salary = 0
            total_net = 0
            
            for worker in self.workers_data:
                worker_id = worker['id']
                rate = worker.get('rate', 0)
                
                # Ishchining soatlarini hisoblash
                worker_hours = 0
                for day in range(1, self.num_days + 1):
                    date_key = f"{self.year}-{self.month:02d}-{day:02d}"
                    hours = self.attendance_data.get((worker_id, date_key), 0)
                    worker_hours += hours
                
                advance = self.advances_data.get(worker_id, 0)
                salary = worker_hours * rate
                net = salary - advance
                
                total_hours += worker_hours
                total_advance += advance
                total_salary += salary
                total_net += net
            
            # Yig'indi qatorini yozish
            summary_labels = ["Jami ishchilar:", "Jami soatlar:", "Jami avans:", "Jami maosh:", "Jami to'lov:"]
            summary_values = [total_workers, total_hours, total_advance, total_salary, total_net]
            
            for i, (label, value) in enumerate(zip(summary_labels, summary_values)):
                col_idx = self.calc_start_col + i
                
                # Label
                label_cell = self.ws.cell(row=self.current_row, column=col_idx - 1, value=label)
                label_cell.font = ExcelStyles.BOLD_FONT
                label_cell.alignment = ExcelStyles.RIGHT
                label_cell.border = ExcelStyles.BORDER
                
                # Value
                value_cell = self.ws.cell(row=self.current_row, column=col_idx, value=value)
                value_cell.font = ExcelStyles.BOLD_FONT
                value_cell.alignment = ExcelStyles.RIGHT
                value_cell.border = ExcelStyles.BORDER
                value_cell.number_format = '#,##0'
            
        except Exception as e:
            logger.error(f"❌ Yig'indi bo'limini yaratishda xatolik: {e}")
    
    def apply_auto_filters(self):
        """Avto filtrlarni qo'llash"""
        try:
            # Sarlavha qatoriga filtrlarni qo'llash
            header_row = 3  # Sanalar sarlavhasi qatori
            last_col = self.calc_start_col + 4
            self.ws.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{self.current_row}"
        except Exception as e:
            logger.warning(f"⚠️ Avto filtrlarni qo'llashda xatolik: {e}")
    
    def generate(self, workers_data: List[Dict], attendance_data: Dict, advances_data: Dict) -> str:
        """Excel hisobotini yaratish"""
        try:
            # Ma'lumotlarni saqlash
            self.workers_data = workers_data
            self.attendance_data = attendance_data
            self.advances_data = advances_data
            
            # Validatsiya
            is_valid, error_msg = self.validate_input_data()
            if not is_valid:
                raise ValueError(f"Ma'lumotlar validatsiyasida xatolik: {error_msg}")
            
            # Excel sozlamalari
            self.setup_column_widths()
            self.create_main_header()
            self.create_dates_header()
            
            # Ishchilarni guruhlash va bo'limlarni yaratish
            grouped_workers = self.group_workers_by_location()
            
            for location, workers in sorted(grouped_workers.items()):
                self.create_location_section(location, workers)
                self.current_row += 1  # Bo'sh qator qo'shish
            
            # Yig'indi bo'limi
            self.create_summary_section()
            
            # Filtrlarni qo'llash
            self.apply_auto_filters()
            
            # Faylni saqlash
            filename = self.save_file()
            
            logger.info(f"✅ Excel hisobot yaratildi: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Excel hisobot yaratishda xatolik: {e}")
            raise
    
    def save_file(self) -> str:
        """Faylni saqlash"""
        try:
            # Fayl nomini yaratish
            filename = f"Hisobot_{self.year}_{self.month:02d}.xlsx"
            
            # Faylni saqlash
            self.wb.save(filename)
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Faylni saqlashda xatolik: {e}")
            raise

# Asosiy funksiya (oldingi interfeys bilan moslashtirilgan)
def generate_report(year: int, month: int, workers_data: List[Dict], 
                   attendance_data: Dict, advances_data: Dict) -> str:
    """
    Excel hisobotini yaratish (oldingi interfeys bilan mos kelishi uchun)
    
    Args:
        year: Yil
        month: Oy
        workers_data: Ishchilar ro'yxati
        attendance_data: Davomat ma'lumotlari {(worker_id, date_str): hours}
        advances_data: Avans ma'lumotlari {worker_id: amount}
    
    Returns:
        str: Yaratilgan fayl nomi
    """
    try:
        generator = AdvancedExcelGenerator(year, month)
        filename = generator.generate(workers_data, attendance_data, advances_data)
        return filename
    except Exception as e:
        logger.error(f"❌ Generate reportda xatolik: {e}")
        
        # Nisbatan xavfsiz alternativ
        try:
            simple_filename = f"Hisobot_{month}_{year}.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "Xato"
            ws['A1'] = f"Hisobot yaratishda xatolik: {str(e)}"
            wb.save(simple_filename)
            return simple_filename
        except:
            return f"Hisobot_{month}_{year}_error.xlsx"

# Qo'shimcha funksiya: Joriy oy uchun hisobot
def generate_current_month_report(workers_data: List[Dict], 
                                attendance_data: Dict, 
                                advances_data: Dict) -> str:
    """Joriy oy uchun hisobot yaratish"""
    now = datetime.now()
    return generate_report(now.year, now.month, workers_data, attendance_data, advances_data)

# Qo'shimcha funksiya: Oldingi oy uchun hisobot
def generate_previous_month_report(workers_data: List[Dict], 
                                 attendance_data: Dict, 
                                 advances_data: Dict) -> str:
    """Oldingi oy uchun hisobot yaratish"""
    now = datetime.now()
    if now.month == 1:
        year = now.year - 1
        month = 12
    else:
        year = now.year
        month = now.month - 1
    
    return generate_report(year, month, workers_data, attendance_data, advances_data)
