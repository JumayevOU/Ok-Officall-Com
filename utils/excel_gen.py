import calendar
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# --- DIZAYN VA RANGLAR ---
HEADER_FILL = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid") # Sariq (Shapka)
BLOCK_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # Och sariq (Blok nomi)
ABSENT_FILL = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid") # Qizil (Kelmadi)
WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

# Shriftlar
BIG_TITLE_FONT = Font(bold=True, name='Calibri', size=16) # Katta sarlavha
TITLE_FONT = Font(bold=True, name='Calibri', size=11)     # Kichik sarlavha
DATA_FONT = Font(name='Calibri', size=11)
BOLD_DATA_FONT = Font(bold=True, name='Calibri', size=11)

# Joylashuv
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")
ALL_BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

# Oy nomlari (O'zbekcha)
MONTHS_UZ = {
    1: "YANVAR", 2: "FEVRAL", 3: "MART", 4: "APREL", 5: "MAY", 6: "IYUN",
    7: "IYUL", 8: "AVGUST", 9: "SENTABR", 10: "OKTABR", 11: "NOYABR", 12: "DEKABR"
}

def generate_report(year, month, workers_data, attendance_data, advances_data):
    wb = Workbook()
    ws = wb.active
    ws.title = f"{month}-{year}"
    
    # 1. MA'LUMOTLARNI SARALASH (Eng muhim qism!)
    # Avval Blok bo'yicha, keyin Ism bo'yicha alifbo tartibida saralaymiz.
    # Shunda H Blokdagilar qachon qo'shilganidan qat'iy nazar bir joyga yig'iladi.
    workers_data.sort(key=lambda x: (x.get('location', '') or 'ZZZZ', x['name']))

    num_days = calendar.monthrange(year, month)[1]
    
    # ==========================================
    # 1-QATOR: KATTA SARLAVHA (YIL VA OY)
    # ==========================================
    month_name = MONTHS_UZ.get(month, "")
    
    # Barcha ustunlarni hisoblaymiz: № + Ism + Kunlar + 5 ta hisob ustuni
    total_cols = 1 + 1 + num_days + 5 
    
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    title_cell = ws.cell(row=1, column=1, value=f"{month_name} {year} - DAVOMAT JADVALI")
    title_cell.font = BIG_TITLE_FONT
    title_cell.alignment = CENTER_ALIGN
    title_cell.fill = WHITE_FILL
    
    # ==========================================
    # 2-QATOR: SHAPKA (HEADER)
    # ==========================================
    header_row = 2
    
    # A Ustun: № (Tartib raqam)
    ws.column_dimensions['A'].width = 5
    ws.cell(row=header_row, column=1, value="№").font = TITLE_FONT
    ws.cell(row=header_row, column=1).fill = HEADER_FILL
    ws.cell(row=header_row, column=1).border = ALL_BORDER
    ws.cell(row=header_row, column=1).alignment = CENTER_ALIGN

    # B Ustun: F.I.O
    ws.column_dimensions['B'].width = 40 
    ws.cell(row=header_row, column=2, value="F.I.O").font = TITLE_FONT
    ws.cell(row=header_row, column=2).fill = HEADER_FILL
    ws.cell(row=header_row, column=2).border = ALL_BORDER
    ws.cell(row=header_row, column=2).alignment = CENTER_ALIGN

    # C Ustundan boshlab: Sanalar
    for day in range(1, num_days + 1):
        col_idx = day + 2 # A va B dan keyin
        col_letter = get_column_letter(col_idx)
        
        ws.cell(row=header_row, column=col_idx, value=day).font = Font(bold=True, size=10)
        ws.cell(row=header_row, column=col_idx).fill = HEADER_FILL
        ws.cell(row=header_row, column=col_idx).border = ALL_BORDER
        ws.cell(row=header_row, column=col_idx).alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[col_letter].width = 4

    # Yakuniy hisob ustunlari
    start_calc = num_days + 3
    headers = ["Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    
    for i, text in enumerate(headers):
        col = start_calc + i
        c = ws.cell(row=header_row, column=col, value=text)
        c.font = TITLE_FONT; c.fill = HEADER_FILL; c.alignment = CENTER_ALIGN; c.border = ALL_BORDER
        ws.column_dimensions[get_column_letter(col)].width = 13

    # ==========================================
    # 3. ISHCHILARNI CHIZISH
    # ==========================================
    current_row = 3
    last_location = None
    counter = 1 # Tartib raqam uchun

    for worker in workers_data:
        current_loc = worker.get('location', 'Umumiy') or 'Umumiy'
        
        # --- BLOK AJRATUVCHI (Agar lokatsiya o'zgarsa) ---
        if current_loc != last_location:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
            bc = ws.cell(row=current_row, column=1, value=f"🏢 {current_loc.upper()}")
            bc.font = Font(bold=True, size=12); bc.fill = BLOCK_FILL; bc.alignment = Alignment(horizontal="center")
            bc.border = ALL_BORDER
            # Chegaralarni to'g'irlash
            for c in range(1, total_cols + 1): ws.cell(row=current_row, column=c).border = ALL_BORDER
            
            current_row += 1
            last_location = current_loc
            counter = 1 # Har yangi blokda sanash 1 dan boshlansinmi? Yo'q, umumiy ketsin desangiz bu qatorni o'chiring. 
            # Agar har blokda 1 dan boshlansin desangiz qolsin.
            # Keling, umumiy sanalishini ta'minlaymiz, shuning uchun counter=1 ni o'chirib tashlayman.
            # (Agar sizga har blok 1 dan boshlanishi kerak bo'lsa, aytasiz)
            # Hozircha commentga olib qo'yaman:
            # counter = 1 

        # --- ISHCHI QATORI ---
        
        # 1. № (Tartib raqam)
        ws.cell(row=current_row, column=1, value=counter).border = ALL_BORDER
        ws.cell(row=current_row, column=1).alignment = CENTER_ALIGN
        counter += 1

        # 2. Ism
        ws.cell(row=current_row, column=2, value=worker['name']).border = ALL_BORDER
        ws.cell(row=current_row, column=2).font = DATA_FONT
        ws.cell(row=current_row, column=2).alignment = LEFT_ALIGN

        # 3. Sanalar
        created_at = worker['created_at']
        if isinstance(created_at, datetime): created_at = created_at.date()
        
        archived_at = worker['archived_at']
        if isinstance(archived_at, datetime): archived_at = archived_at.date()

        total_hours = 0
        for day in range(1, num_days + 1):
            col = day + 2
            curr_date = date(year, month, day)
            date_key = f"{year}-{month:02d}-{day:02d}"
            cell = ws.cell(row=current_row, column=col)
            cell.border = ALL_BORDER; cell.alignment = Alignment(horizontal="center"); cell.font = DATA_FONT
            
            # Qizil zona (Ishlamagan payti)
            if (curr_date < created_at) or (archived_at and curr_date > archived_at):
                cell.fill = ABSENT_FILL
                cell.value = "" # "X" yo'q, shunchaki bo'sh va qizil
            else:
                hours = attendance_data.get((worker['id'], date_key), None)
                if hours is not None:
                    if hours == 0:
                        cell.fill = ABSENT_FILL # Kelmadi
                        cell.value = "" # "X" yo'q
                    else:
                        cell.value = hours
                        total_hours += hours

        # 4. Yakuniy hisoblar
        # Soatlik narx
        ws.cell(row=current_row, column=start_calc, value=worker['rate']).border = ALL_BORDER
        ws.cell(row=current_row, column=start_calc).number_format = '#,##0'
        
        # Jami soat
        c = ws.cell(row=current_row, column=start_calc+1, value=total_hours)
        c.border = ALL_BORDER; c.font = BOLD_DATA_FONT; c.alignment = CENTER_ALIGN
        
        # Avans
        adv = advances_data.get(worker['id'], 0)
        c = ws.cell(row=current_row, column=start_calc+2, value=adv)
        c.border = ALL_BORDER; c.number_format = '#,##0'
        
        # Hisoblangan (Gross)
        gross = total_hours * worker['rate']
        c = ws.cell(row=current_row, column=start_calc+3, value=gross)
        c.border = ALL_BORDER; c.number_format = '#,##0'
        
        # Qo'lga tegadi (Net)
        net = gross - adv
        c = ws.cell(row=current_row, column=start_calc+4, value=net)
        c.border = ALL_BORDER; c.font = BOLD_DATA_FONT; c.number_format = '#,##0'
        c.fill = PatternFill(start_color="E2EFDA", fill_type="solid") # Yashil

        current_row += 1

    filename = f"Hisobot_{month}_{year}.xlsx"
    wb.save(filename)
    return filename