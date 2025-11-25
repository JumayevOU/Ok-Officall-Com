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
    ws['A1'].font = TITLE_FONT
    ws['A1'].fill = HEADER_FILL
    ws['A1'].alignment = CENTER_ALIGN
    ws['A1'].border = ALL_BORDER

    for day in range(1, num_days + 1):
        col_idx = day + 1
        col_letter = get_column_letter(col_idx)
        ws.cell(row=1, column=col_idx, value=f"{day:02d}.{month:02d}").font = Font(bold=True, size=9)
        ws.cell(row=1, column=col_idx).fill = HEADER_FILL
        ws.cell(row=1, column=col_idx).border = ALL_BORDER
        ws.cell(row=1, column=col_idx).alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[col_letter].width = 6

    start_calc_col = num_days + 2
    headers = ["Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    for i, header in enumerate(headers):
        col = start_calc_col + i
        c = ws.cell(row=1, column=col, value=header)
        c.font = TITLE_FONT; c.fill = HEADER_FILL; c.alignment = CENTER_ALIGN; c.border = ALL_BORDER
        ws.column_dimensions[get_column_letter(col)].width = 14

    grouped_workers = {}
    for w in workers_data:
        loc = w.get('location', 'Boshqa') or 'Boshqa'
        if loc not in grouped_workers: grouped_workers[loc] = []
        grouped_workers[loc].append(w)

    current_row = 2
    for location, workers in grouped_workers.items():
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=start_calc_col + 4)
        bc = ws.cell(row=current_row, column=1, value=f"🏢 {location.upper()}")
        bc.font = Font(bold=True, size=12); bc.fill = BLOCK_FILL; bc.alignment = Alignment(horizontal="center"); bc.border = ALL_BORDER
        for col in range(1, start_calc_col + 5): ws.cell(row=current_row, column=col).border = ALL_BORDER
        current_row += 1

        for worker in workers:
            nc = ws.cell(row=current_row, column=1, value=worker['name'])
            nc.font = DATA_FONT; nc.alignment = LEFT_ALIGN; nc.border = ALL_BORDER
            
            total_hours = 0
            created_at, archived_at = worker['created_at'], worker['archived_at']
            for day in range(1, num_days + 1):
                col = day + 1
                curr_date = date(year, month, day)
                date_key = f"{year}-{month:02d}-{day:02d}"
                cell = ws.cell(row=current_row, column=col)
                cell.border = ALL_BORDER; cell.alignment = Alignment(horizontal="center"); cell.font = DATA_FONT
                
                if (curr_date < created_at) or (archived_at and curr_date > archived_at):
                    cell.fill = ABSENT_FILL; cell.value = "✖️"
                else:
                    hours = attendance_data.get((worker['id'], date_key), None)
                    if hours is not None:
                        if hours == 0: cell.fill = ABSENT_FILL; cell.value = ""
                        else: cell.value = hours; total_hours += hours

            ws.cell(row=current_row, column=start_calc_col, value=worker['rate']).border = ALL_BORDER
            c = ws.cell(row=current_row, column=start_calc_col+1, value=total_hours)
            c.border = ALL_BORDER; c.font = BOLD_DATA_FONT
            adv = advances_data.get(worker['id'], 0)
            ws.cell(row=current_row, column=start_calc_col+2, value=adv).border = ALL_BORDER
            gross = total_hours * worker['rate']
            ws.cell(row=current_row, column=start_calc_col+3, value=gross).border = ALL_BORDER
            net = gross - adv
            cn = ws.cell(row=current_row, column=start_calc_col+4, value=net)
            cn.border = ALL_BORDER; cn.font = BOLD_DATA_FONT; cn.fill = PatternFill(start_color="E2EFDA", fill_type="solid")
            
            current_row += 1
            
    filename = f"Hisobot_{month}_{year}.xlsx"
    wb.save(filename)
    return filename