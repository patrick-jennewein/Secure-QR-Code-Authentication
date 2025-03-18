import sqlite3

def initialize_database():
    # connect to database
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # create the table if it doesn't exist
    print("Table created!")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_data (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            class TEXT,
            qr_code TEXT UNIQUE,
            last_scan_time TEXT DEFAULT NULL
        )
    ''')

    conn.commit()
    conn.close()