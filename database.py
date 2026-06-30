import sqlite3
import os
from config import encrypt_data, decrypt_data

DB_PATH = os.path.join("data", "bot.db")

def connect_db():
    """Маълумотлар базаси папкаси ва файлига хавфсиз уланиш"""
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Бот ишлаши учун зарур бўлган барча жадвалларни яратиш"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # 1. Фойдаланувчилар жадвали (Жинси ва Бан ҳолати)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        gender TEXT DEFAULT NULL,
        is_banned INTEGER DEFAULT 0
    )""")
    
    # 2. Тайёр таҳлил натижалари жадвали (PDF юборилганда шу ерга ёзилади)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis (
        user_id INTEGER PRIMARY KEY,
        result_text TEXT,
        file_id TEXT
    )""")
    
    # 3. Шифокор қабулига ёзилишлар жадвали
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        full_name TEXT,
        doctor_type TEXT,
        details TEXT,
        phone_number TEXT,
        is_answered INTEGER DEFAULT 0,
        date_booked TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # 4. Беморларнинг Face ID таҳлил сўровлари жадвали
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        full_name TEXT,
        passport TEXT,
        jshshir TEXT,
        birth_date TEXT,
        selfie_file_id TEXT,
        date_requested TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()

def add_analysis_request(user_id, full_name, passport, jshshir, birth_date, selfie_id):
    """Бемор юборган маълумотларни базага ШИФРЛАБ ёзиш функцияси"""
    conn = connect_db()
    
    # Паспорт ва ЖШШИР базага киришдан олдин таниб бўлмас ҳолатга келади
    safe_passport = encrypt_data(passport)
    safe_jshshir = encrypt_data(jshshir)
    
    conn.execute(
        "INSERT INTO analysis_requests (user_id, full_name, passport, jshshir, birth_date, selfie_file_id) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, full_name, safe_passport, safe_jshshir, birth_date, selfie_id)
    )
    conn.commit()
    conn.close()

def get_analysis_requests():
    """Админ Excel юклаб олмоқчи бўлганда маълумотларни ШИФРДАН ЕЧИБ бериш функцияси"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, full_name, passport, jshshir, birth_date, date_requested FROM analysis_requests")
    rows = cursor.fetchall()
    conn.close()
    
    decrypted_rows = []
    for r in rows:
        # Ҳар бир қаторни ўқишда шифрдан ечиб (decrypt), тоза ҳолда рўйхатга қўшамиз
        decrypted_rows.append({
            "ID": r[0],
            "Telegram ID": r[1],
            "F.I.Sh (Bemor)": r[2],
            "Pasport Seriya": decrypt_data(r[3]),
            "JSHSHIR (ПИНФЛ)": decrypt_data(r[4]),
            "Tug'ilgan sana": r[5],
            "So'rov vaqti": r[6]
        })
    return decrypted_rows

# Файл ишга тушганда база автоматик созланади
init_db()