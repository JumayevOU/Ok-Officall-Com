import calendar
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="FFD966", fill_type="solid")
BLOCK_FILL = PatternFill(start_color="FFF2CC", fill_type="solid")
ABSENT_FILL = PatternFill(start_color="F4CCCC", fill_type="solid")
WHITE_FILL = PatternFill(start_color="FFFFFF", fill_type="solid")
BIG_TITLE = Font(bold=True, name='Calibri', size=16)
TITLE_FONT = Font(bold=True, name='Calibri', size=11)
DATA_FONT = Font(name='Calibri', size=11)
BOLD_DATA = Font(bold=True, name='Calibri', size=11)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")
ALL_BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

MONTHS = {1:"YANVAR", 2:"FEVRAL", 3:"MART", 4:"APREL", 5:"MAY", 6:"IYUN", 7:"IYUL", 8:"AVGUST", 9:"SENTABR", 10:"OKTABR", 11:"NOYABR", 12:"DEKABR"}

def generate_report(year, month, workers_data, attendance_data, advances_data):
    wb = Workbook(); ws = wb.active
    ws.title = f"{month}-{year}"
    workers_data.sort(key=lambda x: (x.get('location', '') or 'ZZZZ', x['name']))
    num_days = calendar.monthrange(year, month)[1]
    
    total_cols = num_days + 7
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    ws.cell(row=1, column=1, value=f"{MONTHS.get(month,'')} {year} - DAVOMAT").font = BIG_TITLE
    ws.cell(row=1, column=1).alignment = CENTER_ALIGN; ws.cell(row=1, column=1).fill = WHITE_FILL

    ws.column_dimensions['A'].width = 5; ws.column_dimensions['B'].width = 40
    ws.cell(row=2, column=1, value="№").font = TITLE_FONT
    ws.cell(row=2, column=2, value="F.I.O").font = TITLE_FONT
    for c in [1,2]: 
        ws.cell(row=2, column=c).fill=HEADER_FILL; ws.cell(row=2, column=c).border=ALL_BORDER; ws.cell(row=2, column=c).alignment=CENTER_ALIGN

    for d in range(1, num_days + 1):
        col = d + 2
        ws.cell(row=2, column=col, value=d).font = Font(bold=True, size=10)
        ws.cell(row=2, column=col).fill=HEADER_FILL; ws.cell(row=2, column=col).border=ALL_BORDER; ws.cell(row=2, column=col).alignment=CENTER_ALIGN
        ws.column_dimensions[get_column_letter(col)].width = 4

    start_calc = num_days + 3
    headers = ["Soatlik", "Jami Soat", "Avans", "Hisoblangan", "Qo'lga Tegadi"]
    for i, t in enumerate(headers):
        col = start_calc + i
        ws.cell(row=2, column=col, value=t).font = TITLE_FONT
        ws.cell(row=2, column=col).fill=HEADER_FILL; ws.cell(row=2, column=col).border=ALL_BORDER; ws.cell(row=2, column=col).alignment=CENTER_ALIGN
        ws.column_dimensions[get_column_letter(col)].width = 13

    row = 3; last_loc = None; counter = 1
    for w in workers_data:
        curr_loc = w.get('location', 'Umumiy') or 'Umumiy'
        if curr_loc != last_loc:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=total_cols)
            ws.cell(row=row, column=1, value=f"🏢 {curr_loc.upper()}").font = Font(bold=True, size=12)
            ws.cell(row=row, column=1).fill=BLOCK_FILL; ws.cell(row=row, column=1).alignment=Alignment(horizontal="center"); ws.cell(row=row, column=1).border=ALL_BORDER
            for c in range(1, total_cols+1): ws.cell(row=row, column=c).border=ALL_BORDER
            row += 1; last_loc = curr_loc

        ws.cell(row=row, column=1, value=counter).border=ALL_BORDER; ws.cell(row=row, column=1).alignment=CENTER_ALIGN
        ws.cell(row=row, column=2, value=w['name']).border=ALL_BORDER; ws.cell(row=row, column=2).font=DATA_FONT
        counter += 1

        # DATE TYPE FIX
        created_at = w['created_at']
        if isinstance(created_at, datetime): created_at = created_at.date()
        archived_at = w['archived_at']
        if isinstance(archived_at, datetime): archived_at = archived_at.date()

        tot_h = 0
        for d in range(1, num_days + 1):
            col = d + 2
            curr = date(year, month, d)
            dk = f"{year}-{month:02d}-{d:02d}"
            cell = ws.cell(row=row, column=col)
            cell.border=ALL_BORDER; cell.alignment=CENTER_ALIGN; cell.font=DATA_FONT
            
            if (curr < created_at) or (archived_at and curr > archived_at):
                cell.fill = ABSENT_FILL
            else:
                h = attendance_data.get((w['id'], dk), None)
                if h is not None:
                    if h == 0: cell.fill = ABSENT_FILL
                    else: cell.value = h; tot_h += h

        ws.cell(row=row, column=start_calc, value=w['rate']).border=ALL_BORDER; ws.cell(row=row, column=start_calc).number_format='#,##0'
        ws.cell(row=row, column=start_calc+1, value=tot_h).border=ALL_BORDER; ws.cell(row=row, column=start_calc+1).font=BOLD_DATA
        adv = advances_data.get(w['id'], 0)
        ws.cell(row=row, column=start_calc+2, value=adv).border=ALL_BORDER; ws.cell(row=row, column=start_calc+2).number_format='#,##0'
        gross = tot_h * w['rate']
        ws.cell(row=row, column=start_calc+3, value=gross).border=ALL_BORDER; ws.cell(row=row, column=start_calc+3).number_format='#,##0'
        net = gross - adv
        c = ws.cell(row=row, column=start_calc+4, value=net)
        c.border=ALL_BORDER; c.font=BOLD_DATA; c.number_format='#,##0'; c.fill=PatternFill(start_color="E2EFDA", fill_type="solid")
        row += 1

    fname = f"Hisobot_{month}_{year}.xlsx"
    wb.save(fname)
    return fname