import pandas as pd
import os
from datetime import datetime, timedelta

def get_tashkent_time():
    return datetime.utcnow() + timedelta(hours=5)

def generate_report(year, month, workers, attendance_dict, advances_dict):
    """Excel hisobot yaratish"""
    
    data = []
    
    for worker in workers:
        w_id = worker['id']
        name = worker['name']
        rate = float(worker['rate'])
        
        # Jami soat
        worker_hours = 0
        for (a_id, date_str), hours in attendance_dict.items():
            if a_id == w_id:
                worker_hours += hours
        
        # Jami avans
        worker_advance = advances_dict.get(w_id, 0.0)
        
        salary = worker_hours * rate
        net_salary = salary - worker_advance
        
        row = {
            "ID": w_id,
            "F.I.SH": name,
            "Stavka": rate,
            "Ishlangan soat": worker_hours,
            "Avans": worker_advance,
            "Hisoblangan": salary,
            "Qo'lga tegadi": net_salary
        }
        data.append(row)
        
    df = pd.DataFrame(data)
    
    now = get_tashkent_time()
    filename = f"Hisobot_{year}_{month}_{now.strftime('%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Hisobot', index=False)
        
        # Kenglikni to'g'irlash
        worksheet = writer.sheets['Hisobot']
        for i, col in enumerate(df.columns):
            worksheet.set_column(i, i, 20)
            
    return filename


