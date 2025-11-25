import calendar
from datetime import datetime
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import os

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# Logger sozlamalari
logger = logging.getLogger(__name__)

# Style konstantalari
class ExcelStyles:
    """Excel stil konstantalari"""
    YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    GREEN_FILL = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
    GRAY_FILL = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
    
    BOLD_FONT = Font(bold=True, name='Arial', size=10)
    HEADER_FONT = Font(bold=True, name='Arial', size=12, color="000000")
    NORMAL_FONT = Font(name='Arial', size=9)
    
    ROTATE_TEXT = Alignment(text_rotation=90, horizontal="center", vertical="center")
    CENTER = Alignment(horizontal="center", vertical="center")
    LEFT = Alignment(horizontal="left", vertical="center")
    RIGHT = Alignment(horizontal="right", vertical="center")
    
    THIN_BORDER = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'), 
        bottom=Side(style='thin')
    )
    MEDIUM_BORDER = Border(
        left=Side(style='medium'), 
        right=Side(style='medium'), 
        top=Side(style='medium'), 
        bottom=Side(style='medium')
    )

class ExcelReportGenerator:
    """Excel hisobot generatori"""
    
    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.num_days = calendar.monthrange(year, month)[1]
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = f"Davomat {month:02d}.{year}"
        
        # Ma'lumotlar
        self.workers_data = []
        self.attendance_data = {}
        self.advances_data = {}
        
        # Hisoblar
        self.current_row = 1
        self.start_calc_col = 0
        
    def validate_input_data(self) -> Tuple[bool, str]:
        """Kirish ma'lumotlarini tekshirish"""
        if not self.workers_data:
            return False, "Ishchilar ma'lumotlari bo'sh"
        
        if not isinstance(self.attendance_data, dict):
            return False, "Davomat ma'lumotlari noto'g'ri formatda"
        
        if not isinstance(self.advances_data, dict):
            return False, "Avans ma'lumotlari noto'g'ri formatda"
        
        if self.month < 1 or self.month > 12:
            return False, "Oy noto'g'ri (1-12 oralig'ida bo'lishi kerak)"
        
        if self.year < 2000 or self.year > 2100:
            return False, "Yil noto'g'ri"
        
        return True, "OK"
    
    def setup_column_widths(self):
        """Ustun kengliklarini sozlash"""
        try:
            # Asosiy ustunlar
            self.ws.column_dimensions['A'].width = 30  # Ism
            self.ws.column_dimensions['B'].width = 15  # Lokatsiya
            
            # Kunlar uchun tor ustunlar
            for day in range(1, self.num_days + 1):
                col_letter = get_column_letter(day + 2)  # C, D, E, ...
                self.ws.column_dimensions[col_letter].width = 4
            
            # Hisoblash ustunlari
            calc_columns = 6
            for i in range(calc_columns):
                col_letter = get_column_letter(self.start_calc_col + i)
                self.ws.column_dimensions[col_letter].width = 12
                
        except Exception as e:
            logger.error(f"❌ Ustun kengliklarini sozlashda xatolik: {e}")
    
    def create_header(self):
        """Sarlavha yaratish"""
        try:
            # Asosiy sarlavha
            self.ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=self.start_calc_col + 5)
            title_cell = self.ws.cell(row=1, column=1, 
                                    value=f"DAVOMAT HISOBOTI - {self.month:02d}.{self.year}")
            title_cell.font = Font(bold=True, name='Arial', size=14, color="000080")
            title_cell.alignment = ExcelStyles.CENTER
            title_cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
            
            self.current_row = 3
            
            # Jadval sarlavhasi
            headers = ["F.I.O", "Lokatsiya"]  # Lokatsiya qo'shildi
            
            # Kunlar
            for day in range(1, self.num_days + 1):
                date_str = f"{day:02d}"
                headers.append(date_str)
            
            # Hisoblash ustunlari
            calc_headers = ["Soatlik Narx", "Jami Soat", "O'rtacha", "Avans", "Jami Maosh", "Qo'lga Tegadi"]
            headers.extend(calc_headers)
            
            # Sarlavha qatorini yozish
            for col_idx, header in enumerate(headers, 1):
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=header)
                cell.font = ExcelStyles.BOLD_FONT
                cell.alignment = ExcelStyles.CENTER
                cell.fill = ExcelStyles.YELLOW_FILL
                cell.border = ExcelStyles.THIN_BORDER
                
                # Kunlar ustunlariga aylantirish
                if 3 <= col_idx <= self.num_days + 2:
                    cell.alignment = ExcelStyles.ROTATE_TEXT
            
            self.start_calc_col = self.num_days + 3  # Hisoblash ustunlari boshlanishi
            self.current_row += 1
            
        except Exception as e:
            logger.error(f"❌ Sarlavha yaratishda xatolik: {e}")
            raise
    
    def group_workers_by_location(self) -> Dict[str, List[Dict]]:
        """Ishchilarni lokatsiya bo'yicha guruhlash"""
        grouped = {}
        for worker in self.workers_data:
            loc = worker.get('location', 'Noma\'lum') or 'Noma\'lum'
            if loc not in grouped:
                grouped[loc] = []
            grouped[loc].append(worker)
        return grouped
    
    def create_location_section(self, location: str, workers: List[Dict]):
        """Lokatsiya bo'limini yaratish"""
        try:
            # Lokatsiya sarlavhasi
            end_col = self.start_calc_col + 5
            self.ws.merge_cells(start_row=self.current_row, start_column=1, 
                               end_row=self.current_row, end_column=end_col)
            
            location_cell = self.ws.cell(row=self.current_row, column=1, 
                                       value=f"📍 {location.upper()}")
            location_cell.font = ExcelStyles.HEADER_FONT
            location_cell.alignment = ExcelStyles.CENTER
            location_cell.fill = ExcelStyles.GREEN_FILL
            
            # Border qo'shish
            for col in range(1, end_col + 1):
                self.ws.cell(row=self.current_row, column=col).border = ExcelStyles.THIN_BORDER
            
            self.current_row += 1
            
            # Ishchilar ma'lumotlari
            for worker in workers:
                self.add_worker_row(worker)
            
            # Bo'sh qator
            self.current_row += 1
            
        except Exception as e:
            logger.error(f"❌ Lokatsiya bo'limini yaratishda xatolik: {e}")
            raise
    
    def add_worker_row(self, worker: Dict[str, Any]):
        """Ishchi qatorini qo'shish"""
        try:
            # Asosiy ma'lumotlar
            self.ws.cell(row=self.current_row, column=1, value=worker['name']).border = ExcelStyles.THIN_BORDER
            self.ws.cell(row=self.current_row, column=2, value=worker.get('location', '')).border = ExcelStyles.THIN_BORDER
            
            total_hours = 0
            work_days = 0
            
            # Davomat ma'lumotlari
            for day in range(1, self.num_days + 1):
                col_idx = day + 2  # C ustunidan boshlanadi
                date_key = f"{self.year}-{self.month:02d}-{day:02d}"
                hours = self.attendance_data.get((worker['id'], date_key))
                
                cell = self.ws.cell(row=self.current_row, column=col_idx)
                cell.border = ExcelStyles.THIN_BORDER
                cell.alignment = ExcelStyles.CENTER
                cell.font = ExcelStyles.NORMAL_FONT
                
                if hours is not None:
                    if hours == 0:
                        cell.fill = ExcelStyles.RED_FILL
                        cell.value = ""  # 0 soat bo'lsa bo'sh qoldirish
                    else:
                        cell.value = hours
                        total_hours += hours
                        work_days += 1
            
            # Hisob-kitoblar
            rate = worker.get('rate', 0)
            advance = self.advances_data.get(worker['id'], 0)
            total_salary = total_hours * rate
            average_hours = total_hours / work_days if work_days > 0 else 0
            net_salary = total_salary - advance
            
            # Hisoblash ustunlari
            calc_cells = [
                (rate, ExcelStyles.RIGHT),
                (total_hours, ExcelStyles.CENTER),
                (round(average_hours, 1), ExcelStyles.CENTER),
                (advance, ExcelStyles.RIGHT),
                (total_salary, ExcelStyles.RIGHT),
                (net_salary, ExcelStyles.RIGHT)
            ]
            
            for i, (value, alignment) in enumerate(calc_cells):
                col_idx = self.start_calc_col + i
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=value)
                cell.border = ExcelStyles.THIN_BORDER
                cell.alignment = alignment
                cell.font = ExcelStyles.NORMAL_FONT
                
                # Format raqamlar
                if isinstance(value, (int, float)):
                    cell.number_format = '#,##0'
            
            # Qo'lga tegadi ustunini qalin qilish
            net_cell = self.ws.cell(row=self.current_row, column=self.start_calc_col + 5)
            net_cell.font = ExcelStyles.BOLD_FONT
            
            # Agar qoldiq manfiy bo'lsa, qizil rang
            if net_salary < 0:
                net_cell.fill = ExcelStyles.RED_FILL
            
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
            end_col = self.start_calc_col + 5
            self.ws.merge_cells(start_row=self.current_row, start_column=1, 
                               end_row=self.current_row, end_column=end_col)
            
            summary_cell = self.ws.cell(row=self.current_row, column=1, 
                                      value="📊 UMUMIY YIG'INDI")
            summary_cell.font = ExcelStyles.HEADER_FONT
            summary_cell.alignment = ExcelStyles.CENTER
            summary_cell.fill = ExcelStyles.GRAY_FILL
            
            for col in range(1, end_col + 1):
                self.ws.cell(row=self.current_row, column=col).border = ExcelStyles.THIN_BORDER
            
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
            summary_data = [
                f"Jami ishchilar: {total_workers}",
                "",
                f"Jami soatlar: {total_hours}",
                f"Jami avans: {total_advance:,.0f}",
                f"Jami maosh: {total_salary:,.0f}",
                f"Jami to'lov: {total_net:,.0f}"
            ]
            
            for i, value in enumerate(summary_data):
                col_idx = self.start_calc_col + i
                cell = self.ws.cell(row=self.current_row, column=col_idx, value=value)
                cell.border = ExcelStyles.THIN_BORDER
                cell.font = ExcelStyles.BOLD_FONT
                cell.alignment = ExcelStyles.LEFT
                
                if i >= 2:  # Raqamli qiymatlar
                    cell.alignment = ExcelStyles.RIGHT
            
        except Exception as e:
            logger.error(f"❌ Yig'indi bo'limini yaratishda xatolik: {e}")
    
    def apply_auto_filters(self):
        """Avto filtrlarni qo'llash"""
        try:
            # Sarlavha qatoriga filtrlarni qo'llash
            header_row = 3
            last_col = self.start_calc_col + 5
            self.ws.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{header_row}"
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
            self.create_header()
            
            # Ishchilarni guruhlash va bo'limlarni yaratish
            grouped_workers = self.group_workers_by_location()
            
            for location, workers in sorted(grouped_workers.items()):
                self.create_location_section(location, workers)
            
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
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            filename = reports_dir / f"Hisobot_{self.year}_{self.month:02d}.xlsx"
            
            # Faylni saqlash
            self.wb.save(filename)
            
            return str(filename)
            
        except PermissionError:
            logger.error("❌ Fayl yozish uchun ruxsat yo'q")
            raise
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
        generator = ExcelReportGenerator(year, month)
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

# Qo'shimcha funksiya: Fayl mavjudligini tekshirish
def check_report_exists(year: int, month: int) -> Optional[str]:
    """Hisobot fayli mavjudligini tekshirish"""
    try:
        filename = f"reports/Hisobot_{year}_{month:02d}.xlsx"
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        logger.error(f"❌ Fayl mavjudligini tekshirishda xatolik: {e}")
        return None

# Qo'shimcha funksiya: Eski hisobotlarni o'chirish
def cleanup_old_reports(days_old: int = 30):
    """Eski hisobot fayllarini o'chirish"""
    try:
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for file_path in reports_dir.glob("Hisobot_*.xlsx"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                file_path.unlink()
                logger.info(f"✅ Eski fayl o'chirildi: {file_path}")
                
    except Exception as e:
        logger.error(f"❌ Eski fayllarni o'chirishda xatolik: {e}")