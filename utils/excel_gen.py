import calendar
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
BLOCK_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
ABSENT_FILL = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")
TITLE_FONT = Font(bold=True, name='Calibri', size=11)
DATA_FONT = Font(name='Calibri', size=11)
BOLD_DATA_FONT = Font(bold=True, name='Calibri', size=11)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")
ALL_BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

def generate_report(year, month, workers_data, attendance_data, advances_data):
    wb = Workbook()
    ws = wb.active
    ws.title = f"{month}-{year}"
    num_days = calendar.monthrange(year, month)[1]
    
    ws.column_dimensions['A'].width = 40 
    ws['A1'] = "F.I.O"
    ws['A1'].font = TITLE_FONT; ws['A1'].fill = HEADER_FILL; ws['A1'].alignment = CENTER_ALIGN; ws['A1'].border = ALL_BORDER

    for day in range(1, num_days + 1):
        col = day + 1
        ws.cell(row=1, column=col, value=f"{day:02d}.{month:02d}").font = Font(bold=True, size=9)
        ws.cell(row=1, column=col).fill = HEADER_FILL; ws.cell(row=1, column=col).border = ALL_BORDER
        ws.cell(row=1, column=col).alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col)].width = 6

    start_calc = num_days + 2
    headers = ["Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    for i, h in enumerate(headers):
        col = start_calc + i
        c = ws.cell(row=1, column=col, value=h)
        c.font = TITLE_FONT; c.fill = HEADER_FILL; c.alignment = CENTER_ALIGN; c.border = ALL_BORDER
        ws.column_dimensions[get_column_letter(col)].width = 14

    grouped = {}
    for w in workers_data:
        loc = w.get('location', 'Boshqa') or 'Boshqa'
        if loc not in grouped: grouped[loc] = []
        grouped[loc].append(w)

    row = 2
    for loc, workers in grouped.items():
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=start_calc + 4)
        bc = ws.cell(row=row, column=1, value=f"🏢 {loc.upper()}")
        bc.font = Font(bold=True, size=12); bc.fill = BLOCK_FILL; bc.alignment = Alignment(horizontal="center"); bc.border = ALL_BORDER
        for c in range(1, start_calc + 5): ws.cell(row=row, column=c).border = ALL_BORDER
        row += 1

        for w in workers:
            ws.cell(row=row, column=1, value=w['name']).font = DATA_FONT; ws.cell(row=row, column=1).alignment = LEFT_ALIGN
            ws.cell(row=row, column=1).border = ALL_BORDER
            
            # --- XATOLIK TUZATILDI (DATE CONVERSION) ---
            created_at = w['created_at']
            if isinstance(created_at, datetime): created_at = created_at.date()
            
            archived_at = w['archived_at']
            if isinstance(archived_at, datetime): archived_at = archived_at.date()
            # -------------------------------------------

            total_hours = 0
            for day in range(1, num_days + 1):
                col = day + 1
                curr_date = date(year, month, day)
                date_key = f"{year}-{month:02d}-{day:02d}"
                cell = ws.cell(row=row, column=col)
                cell.border = ALL_BORDER; cell.alignment = Alignment(horizontal="center"); cell.font = DATA_FONT
                
                if (curr_date < created_at) or (archived_at and curr_date > archived_at):
                    cell.fill = ABSENT_FILL; cell.value = "✖️"
                else:
                    hours = attendance_data.get((w['id'], date_key), None)
                    if hours is not None:
                        if hours == 0: cell.fill = ABSENT_FILL; cell.value = ""
                        else: cell.value = hours; total_hours += hours

            ws.cell(row=row, column=start_calc, value=w['rate']).border = ALL_BORDER
            ws.cell(row=row, column=start_calc+1, value=total_hours).border = ALL_BORDER; ws.cell(row=row, column=start_calc+1).font = BOLD_DATA_FONT
            
            adv = advances_data.get(w['id'], 0)
            ws.cell(row=row, column=start_calc+2, value=adv).border = ALL_BORDER
            
            gross = total_hours * w['rate']
            ws.cell(row=row, column=start_calc+3, value=gross).border = ALL_BORDER
            
            net = gross - adv
            cn = ws.cell(row=row, column=start_calc+4, value=net)
            cn.border = ALL_BORDER; cn.font = BOLD_DATA_FONT; cn.fill = PatternFill(start_color="E2EFDA", fill_type="solid")
            row += 1
            
    filename = f"Hisobot_{month}_{year}.xlsx"
    wb.save(filename)
    return filename