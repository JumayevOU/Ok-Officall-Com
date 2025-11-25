import calendar
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# --- STYLES (Ranglar va Dizayn) ---
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid") # Sariq
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")    # Qizil (Kelmadi)
BOLD_FONT = Font(bold=True, name='Arial', size=10)
HEADER_FONT = Font(bold=True, name='Arial', size=12)
ROTATE_TEXT = Alignment(text_rotation=90, horizontal="center", vertical="center") # Tikka yozuv
CENTER = Alignment(horizontal="center", vertical="center")
BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

def generate_report(year, month, workers_data, attendance_data, advances_data):
    wb = Workbook()
    ws = wb.active
    ws.title = "Davomat"

    # Oyning oxirgi kunini aniqlash (28, 30 yoki 31)
    num_days = calendar.monthrange(year, month)[1]
    month_name = get_month_name(month).upper()

    # --- 1. SHAPKA QISMI (HEADER) ---
    
    # A ustun: F.I.O
    ws.column_dimensions['A'].width = 30
    ws['A1'] = "F.I.O"
    ws['A1'].font = Font(bold=True, size=16, name='Arial')
    ws['A1'].fill = YELLOW_FILL
    ws['A1'].alignment = CENTER
    ws['A1'].border = BORDER

    # Sanalar (1 dan 30/31 gacha)
    for day in range(1, num_days + 1):
        col_idx = day + 1 # B ustunidan boshlanadi
        col_letter = get_column_letter(col_idx)
        
        # Sana yozish (01.11.2025)
        date_str = f"{day:02d}.{month:02d}.{year}"
        cell = ws.cell(row=1, column=col_idx, value=date_str)
        cell.alignment = ROTATE_TEXT # Tikka qilish
        cell.font = BOLD_FONT
        cell.border = BORDER
        ws.column_dimensions[col_letter].width = 4 # Ingichka ustun

    # Oy Nomi (Tepada o'rtada turishi uchun)
    # Bu yerda biz 1-qatorni sanalar uchun ishlatdik, keling rasmga moslab
    # OY NOMINI sanalar tepasiga alohida qator qilib qo'shsak chiroyli bo'ladi.
    # Lekin rasmda FIO tepasida joy yo'q. Demak, sanalar qatorining o'ng tarafida yoki ustida bo'lishi kerak.
    # Keling, rasmga moslab, sanalarni 1-qatorga qo'yamiz.

    # --- YAKUNIY USTUNLAR (Sanalardan keyin) ---
    start_calc_col = num_days + 2
    headers = ["Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    
    for i, header in enumerate(headers):
        col_idx = start_calc_col + i
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = BOLD_FONT
        cell.alignment = ROTATE_TEXT # Joy tejash uchun tikka qilamiz
        cell.fill = YELLOW_FILL
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = 12

    # --- 2. MA'LUMOTLARNI JOYLASH (BLOKLAR BO'YICHA) ---
    
    # Ishchilarni lokatsiyasi bo'yicha guruhlaymiz
    # workers_data strukturasi: [{'name': 'Ali', 'location': 'H Blok', 'rate': 20000, ...}]
    grouped_workers = {}
    for w in workers_data:
        loc = w['location'] or "Boshqa" # Agar lokatsiya yo'q bo'lsa
        if loc not in grouped_workers: grouped_workers[loc] = []
        grouped_workers[loc].append(w)

    current_row = 2

    for location, workers in grouped_workers.items():
        # --- BLOK AJRATUVCHI QATOR (SARIQ) ---
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=start_calc_col + 4)
        block_cell = ws.cell(row=current_row, column=1, value=f"{location.upper()}")
        block_cell.font = Font(bold=True, size=12)
        block_cell.alignment = CENTER
        block_cell.fill = YELLOW_FILL
        block_cell.border = BORDER
        
        # Qolgan kataklarga ham border berish (merge bo'lsa ham)
        for col in range(1, start_calc_col + 5):
            ws.cell(row=current_row, column=col).border = BORDER
            
        current_row += 1

        # --- ISHCHILAR QATORI ---
        for worker in workers:
            # 1. Ism
            ws.cell(row=current_row, column=1, value=worker['name']).border = BORDER
            
            total_hours = 0
            
            # 2. Sanalar bo'yicha soatlarni qo'yish
            for day in range(1, num_days + 1):
                col_idx = day + 1
                date_key = f"{year}-{month:02d}-{day:02d}"
                
                # Agar shu kunda davomat bo'lsa
                hours = attendance_data.get((worker['id'], date_key), None)
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = BORDER
                cell.alignment = CENTER
                
                if hours is not None:
                    if hours == 0:
                        cell.value = "" # Kelmadi
                        cell.fill = RED_FILL # Qizilga bo'yash
                    else:
                        cell.value = hours
                        total_hours += hours
                
            # 3. Yakuniy hisob-kitob ustunlari
            # Soatlik Narx
            ws.cell(row=current_row, column=start_calc_col, value=worker['rate']).border = BORDER
            
            # Jami soat
            ws.cell(row=current_row, column=start_calc_col+1, value=total_hours).border = BORDER
            
            # Avans (Bazada bor deb hisoblaymiz)
            adv = advances_data.get(worker['id'], 0)
            ws.cell(row=current_row, column=start_calc_col+2, value=adv).border = BORDER
            
            # Hisoblangan (Gross)
            gross = total_hours * worker['rate']
            ws.cell(row=current_row, column=start_calc_col+3, value=gross).border = BORDER
            
            # Qo'lga tegadi (Net)
            net = gross - adv
            ws.cell(row=current_row, column=start_calc_col+4, value=net).border = BORDER
            ws.cell(row=current_row, column=start_calc_col+4).font = BOLD_FONT

            current_row += 1

    filename = f"Hisobot_{get_month_name(month)}_{year}.xlsx"
    wb.save(filename)
    return filename

def get_month_name(month_num):
    months = ["", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    return months[month_num]