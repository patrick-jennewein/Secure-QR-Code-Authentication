import csv
from colorama import init, Fore
import os
from qr_utils import generate_qr_code


def generate_and_store_initial_qr_codes(cursor, folder_path):
    """generate and store QR codes for all students when initially creating the SQL table."""

    # Ensure the folder exists
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(Fore.GREEN + f"Created folder: {folder_path}" + Fore.RESET)
        except OSError as e:
            print(Fore.RED +f"Error creating folder {folder_path}: {e}" + Fore.RESET)
            return

    cursor.execute("SELECT student_id, name, class FROM qr_data WHERE qr_code IS NULL")
    students = cursor.fetchall()

    for student_id, name, class_name in students:
        qr_code_binary, timestamp = generate_qr_code(student_id, name, class_name, "qr_codes", True)
        if qr_code_binary:
            cursor.execute("UPDATE qr_data SET qr_code = ?, qr_valid_after = ? WHERE student_id = ?",
                           (qr_code_binary, timestamp, student_id))


def create_columns_from_csv(cursor, csv_filename):
    """generate data all students when initially creating the SQL table."""
    with open(csv_filename, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            student_id = row["student_id"].strip()
            name = row["name"].strip()
            class_name = row["class"].strip()

            cursor.execute(
                "INSERT INTO qr_data (student_id, name, class) VALUES (?, ?, ?)",
                (student_id, name, class_name),
            )
    print(Fore.GREEN + f"Initial database population loaded from .csv and stored in SQL" + Fore.RESET)


def initialize_database(conn, cursor):
    # check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qr_data'")
    table_exists = cursor.fetchone()

    # if table does not exist, create it
    if not table_exists:
        cursor.execute('''
            CREATE TABLE qr_data (
                student_id TEXT PRIMARY KEY,
                name TEXT,
                class TEXT,
                qr_code TEXT UNIQUE,
                last_scan_time TEXT DEFAULT NULL,
                qr_valid_after TEXT 
            )
        ''')
        create_columns_from_csv(cursor, "fake_data.csv")
        print(Fore.GREEN + f"SQL database fully initialized" + Fore.RESET)

    conn.commit()

def log_scan_event(status, student_id, student_name, class_name, timestamp, filename="scan_log.csv"):
    """Appends scan event info to a CSV log file."""
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Status", "Student ID", "Name", "Class", "Timestamp"])
        writer.writerow([status, student_id, student_name, class_name, timestamp])
