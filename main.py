import cv2
import csv
import sqlite3
import qrcode
import io
import os
from pyzbar.pyzbar import decode
import datetime
import time


def set_webcam_index(index):
    """sets the index of the webcam that will be used for this application"""
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM


def generate_qr_code(student_id, name, class_name):
    """Generates a unique QR code for a student and returns it as binary data."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Make it part of QR data
    qr_data = f"ID:{student_id}|Name:{name}|Class:{class_name}|TS:{timestamp}"

    qr = qrcode.make(qr_data)

    # Ensure the folder exists
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Overwrite the old QR code file (no timestamp in filename)
    qr_filename = os.path.join(folder_path, f"{student_id}.png")
    qr.save(qr_filename, format="PNG")

    # Convert QR code to binary and return
    with open(qr_filename, "rb") as f:
        qr_binary = f.read()

    print(f"✅ Generated new QR for {student_id} at {timestamp}")
    return qr_binary



def generate_and_store_initial_qr_codes(cursor):
    """generates and stores QR codes for all students when initially creating the SQL table."""
    cursor.execute("SELECT student_id, name, class FROM qr_data WHERE qr_code IS NULL")
    students = cursor.fetchall()

    # loops through each student in the database, creates a QR code, and updates the table
    for student_id, name, class_name in students:
        print(f"QR code created for: {name} ({student_id})")
        qr_code_binary = generate_qr_code(student_id, name, class_name)
        cursor.execute("UPDATE qr_data SET qr_code = ? WHERE student_id = ?", (qr_code_binary, student_id))


def update_qr_code(conn, cursor, student_id):
    """Updates a student's QR code when scanned."""
    cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()

    if student:
        name, class_name = student

        # Generate a new QR code
        qr_code_binary = generate_qr_code(student_id, name, class_name)

        # Debugging: Check if the QR code is actually different
        cursor.execute("SELECT qr_code FROM qr_data WHERE student_id = ?", (student_id,))
        old_qr_code = cursor.fetchone()[0]

        if qr_code_binary == old_qr_code:
            print(f"⚠️ Warning: QR code for {student_id} is identical to the previous one!")
        else:
            cursor.execute("UPDATE qr_data SET qr_code = ? WHERE student_id = ?", (qr_code_binary, student_id))
            conn.commit()
            print(f"✅ QR code updated for student {student_id}")
    else:
        print(f"Student ID {student_id} not found.")




def create_columns_from_csv(cursor, csv_filename):
    with open(csv_filename, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            student_id = row["student_id"].strip()
            name = row["name"].strip()
            class_name = row["class"].strip()

            # insert new student from .csv file
            cursor.execute(
                "INSERT INTO qr_data (student_id, name, class) VALUES (?, ?, ?)",
                (student_id, name, class_name),
            )
    print("Initial database population complete!")



def initialize_database(conn, cursor):
    # check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qr_data'")
    table_exists = cursor.fetchone()

    # if table does not exist
    if not table_exists:
        cursor.execute('''
            CREATE TABLE qr_data (
                student_id TEXT PRIMARY KEY,
                name TEXT,
                class TEXT,
                qr_code TEXT UNIQUE,
                last_scan_time TEXT DEFAULT NULL
            )
        ''')
        create_columns_from_csv(cursor, "fake_data.csv")
        generate_and_store_initial_qr_codes(cursor)
        print("Table created!")

    conn.commit()


def main(webcam_index):
    # open connection to webcam and ensure it opened successfully
    webcam = cv2.VideoCapture(webcam_index)
    if not webcam.isOpened():
        print("Error: Could not open webcam.")
        exit()

    # initialize database
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    initialize_database(conn, cursor)

    # Dictionary to track recent scans and prevent duplicate processing
    recent_scans = {}

    # capture webcam by frame
    while True:
        read, frame = webcam.read()
        if not read:
            print("Error: Could not read frame.")
            break

        # detects and decodes QR codes from each individual frame and returns a list
        qr_codes = decode(frame)
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode("utf-8")

            if qr_data.startswith("ID:"):
                student_id = qr_data.split("|")[0].split(":")[1]

                # Get current timestamp
                current_time = time.time()

                # Cooldown period in seconds
                cooldown_period = 3  # Adjust as needed

                # Check if this student ID was scanned recently
                if student_id in recent_scans:
                    time_since_last_scan = current_time - recent_scans[student_id]
                    if time_since_last_scan < cooldown_period:
                        print(f"⏳ Skipping duplicate scan for {student_id} (cooldown active: {time_since_last_scan:.2f} sec ago)")
                        continue  # Skip processing this scan

                # Update recent scan timestamp
                recent_scans[student_id] = current_time

                # Query the database for student info
                cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
                student = cursor.fetchone()

                if student:
                    name, class_name = student

                    # Get formatted timestamp
                    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Update last_scan_time in the database
                    cursor.execute("UPDATE qr_data SET last_scan_time = ? WHERE student_id = ?", (scan_time, student_id))
                    conn.commit()

                    print(f"📸 Scanned Student ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}")

                    # Display detected student info on the frame
                    cv2.putText(frame, f"ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}",
                                (qr_code.rect.left, qr_code.rect.top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # Update QR code (only if cooldown allows it)
                    update_qr_code(conn, cursor, student_id)

                    # ⚡ Force a short delay to ensure the new QR code is registered
                    print(f"⏳ Waiting {cooldown_period} seconds to ensure the new QR code is in effect...")
                    time.sleep(cooldown_period)

                else:
                    print("❌ Student not found in database.")

        # Show webcam feed with potential QR code overlays
        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # End feed
    webcam.release()
    cv2.destroyAllWindows()
    conn.close()



if __name__ == '__main__':
    webcam_index = set_webcam_index(1)
    main(webcam_index)
