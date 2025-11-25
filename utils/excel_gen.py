import calendar
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# Dizayn Ranglari
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
HEADER_FONT = Font(bold=True, name='Arial', size=11)
BOLD_FONT = Font(bold=True, name='Arial', size=10)
ROTATE_TEXT = Alignment(text_rotation=90, horizontal="center", vertical="center")
CENTER = Alignment(horizontal="center", vertical="center")
BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

def generate_report(year, month, workers_data, attendance_data, advances_data):
    wb = Workbook()
    ws = wb.active
    ws.title = "Davomat"

    num_days = calendar.monthrange(year, month)[1]
    
    # 1. SHAPKA QISMI
    ws.column_dimensions['A'].width = 30
    ws['A1'] = "F.I.O"
    ws['A1'].font = HEADER_FONT
    ws['A1'].fill = YELLOW_FILL
    ws['A1'].alignment = CENTER
    ws['A1'].border = BORDER

    # Sanalar (1..31)
    for day in range(1, num_days + 1):
        col_idx = day + 1
        col_letter = get_column_letter(col_idx)
        date_str = f"{day:02d}.{month:02d}.{year}"
        
        cell = ws.cell(row=1, column=col_idx, value=date_str)
        cell.alignment = ROTATE_TEXT
        cell.font = BOLD_FONT
        cell.border = BORDER
        ws.column_dimensions[col_letter].width = 4

    # Yakuniy hisob ustunlari
    start_calc_col = num_days + 2
    headers = ["Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    
    for i, header in enumerate(headers):
        col_idx = start_calc_col + i
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.alignment = ROTATE_TEXT
        cell.fill = YELLOW_FILL
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = 13

    # 2. GURUHLASH (A Blok, H Blok...)
    grouped_workers = {}
    for w in workers_data:
        loc = w.get('location', 'Boshqa') or 'Boshqa'
        if loc not in grouped_workers: grouped_workers[loc] = []
        grouped_workers[loc].append(w)

    current_row = 2
    
    # Ma'lumotlarni chizish
    for location, workers in grouped_workers.items():
        # --- BLOK NOMI ---
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=start_calc_col + 4)
        block_cell = ws.cell(row=current_row, column=1, value=f"{location.upper()}")
        block_cell.font = Font(bold=True, size=12)
        block_cell.alignment = CENTER
        block_cell.fill = YELLOW_FILL
        block_cell.border = BORDER
        
        # Border chizib chiqish (Merge qilingan joyga)
        for col in range(1, start_calc_col + 5):
            ws.cell(row=current_row, column=col).border = BORDER
        current_row += 1

        # --- ISHCHILAR ---
        for worker in workers:
            ws.cell(row=current_row, column=1, value=worker['name']).border = BORDER
            total_hours = 0
            
            # Davomat kunlari
            for day in range(1, num_days + 1):
                col_idx = day + 1
                date_key = f"{year}-{month:02d}-{day:02d}"
                hours = attendance_data.get((worker['id'], date_key), None)
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = BORDER
                cell.alignment = CENTER
                
                if hours is not None:
                    if hours == 0:
                        cell.fill = RED_FILL # Qizil
                        cell.value = ""
                    else:
                        cell.value = hours
                        total_hours += hours
                
            # Hisob-kitoblar
            ws.cell(row=current_row, column=start_calc_col, value=worker['rate']).border = BORDER
            ws.cell(row=current_row, column=start_calc_col+1, value=total_hours).border = BORDER
            
            adv = advances_data.get(worker['id'], 0)
            ws.cell(row=current_row, column=start_calc_col+2, value=adv).border = BORDER
            
            gross = total_hours * worker['rate']
            ws.cell(row=current_row, column=start_calc_col+3, value=gross).border = BORDER
            
            net = gross - adv
            ws.cell(row=current_row, column=start_calc_col+4, value=net).border = BORDER
            ws.cell(row=current_row, column=start_calc_col+4).font = BOLD_FONT

            current_row += 1

    filename = f"Hisobot_{month}_{year}.xlsx"
    wb.save(filename)
    return filename