import cv2
import csv
import sqlite3
import qrcode
import os
from pyzbar.pyzbar import decode
import datetime
import time


def set_webcam_index(index):
    """Sets the index of the webcam that will be used for this application"""
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM



def generate_qr_code(student_id, name, class_name):
    """Generates a unique QR code for a student with a timestamp and returns it as binary data."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Store timestamp in QR data
    qr_data = f"ID:{student_id}|Name:{name}|Class:{class_name}|TS:{timestamp}"

    # Ensure the folder exists
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(f"📂 Created folder: {folder_path}")
        except OSError as e:
            print(f"❌ Error creating folder {folder_path}: {e}")
            return None, None  # Return None if the folder cannot be created

    # Save the new QR code image
    qr = qrcode.make(qr_data)
    qr_filename = os.path.join(folder_path, f"{student_id}.png")
    qr.save(qr_filename, format="PNG")

    # Convert QR code to binary and return
    with open(qr_filename, "rb") as f:
        qr_binary = f.read()

    print(f"✅ Generated new QR for {student_id} at {timestamp}")
    return qr_binary, timestamp


def update_qr_code(conn, cursor, student_id):
    """Updates a student's QR code and invalidates old ones."""
    cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()

    if student:
        name, class_name = student

        # Generate a new QR code and get a new timestamp
        qr_code_binary, new_timestamp = generate_qr_code(student_id, name, class_name)

        # Update the database with the new QR code and set valid timestamp
        cursor.execute("UPDATE qr_data SET qr_code = ?, qr_valid_after = ? WHERE student_id = ?",
                       (qr_code_binary, new_timestamp, student_id))
        conn.commit()
        print(f"✅ QR code updated for student {student_id}. Old QR codes are now invalid.")
    else:
        print(f"❌ Student ID {student_id} not found.")

def generate_and_store_initial_qr_codes(cursor):
    """Generates and stores QR codes for all students when initially creating the SQL table."""

    # Ensure the `qr_codes` folder exists
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(f"📂 Created folder: {folder_path}")
        except OSError as e:
            print(f"❌ Error creating folder {folder_path}: {e}")
            return

    cursor.execute("SELECT student_id, name, class FROM qr_data WHERE qr_code IS NULL")
    students = cursor.fetchall()

    for student_id, name, class_name in students:
        qr_code_binary, timestamp = generate_qr_code(student_id, name, class_name)
        if qr_code_binary:
            cursor.execute("UPDATE qr_data SET qr_code = ?, qr_valid_after = ? WHERE student_id = ?",
                           (qr_code_binary, timestamp, student_id))

def create_columns_from_csv(cursor, csv_filename):
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
    print("Initial database population complete!")


def initialize_database(conn, cursor):
    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qr_data'")
    table_exists = cursor.fetchone()

    # If table does not exist, create it
    if not table_exists:
        cursor.execute('''
            CREATE TABLE qr_data (
                student_id TEXT PRIMARY KEY,
                name TEXT,
                class TEXT,
                qr_code TEXT UNIQUE,
                last_scan_time TEXT DEFAULT NULL,
                qr_valid_after TEXT  -- Column to track when a QR code becomes valid
            )
        ''')
        create_columns_from_csv(cursor, "fake_data.csv")
        print("✅ Table created!")

    conn.commit()


def main(webcam_index):
    # Open connection to webcam and ensure it opened successfully
    webcam = cv2.VideoCapture(webcam_index)
    if not webcam.isOpened():
        print("❌ Error: Could not open webcam.")
        exit()

    # Initialize database
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    initialize_database(conn, cursor)

    # Ensure the `qr_codes` folder exists before generating any QR codes
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(f"📂 Created folder: {folder_path}")
        except OSError as e:
            print(f"❌ Error creating folder {folder_path}: {e}")
            exit()

    # Generate initial QR codes if needed
    generate_and_store_initial_qr_codes(cursor)

    # Dictionary to track recent scans and prevent duplicate processing
    recent_scans = {}

    # Capture webcam frames
    while True:
        read, frame = webcam.read()
        if not read:
            print("❌ Error: Could not read frame.")
            break

        # Detects and decodes QR codes from each frame
        qr_codes = decode(frame)
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode("utf-8")

            if qr_data.startswith("ID:"):
                qr_data_dict = {}

                # Safely parse QR code data into a dictionary
                for part in qr_data.split("|"):
                    key_value = part.split(":", 1)  # Split only at the first `:`
                    if len(key_value) == 2:
                        key, value = key_value
                        qr_data_dict[key.strip()] = value.strip()

                # Ensure required fields exist
                if "ID" not in qr_data_dict or "TS" not in qr_data_dict:
                    print("❌ Invalid QR code format. Skipping...")
                    continue

                student_id = qr_data_dict["ID"]
                scanned_timestamp = qr_data_dict["TS"]

                # Get current time
                current_time = time.time()
                cooldown_period = 1.5  # Cooldown time in seconds

                # Check if this student ID was scanned recently
                if student_id in recent_scans:
                    time_since_last_scan = current_time - recent_scans[student_id]
                    if time_since_last_scan < cooldown_period:
                        continue

                # Update recent scan timestamp
                recent_scans[student_id] = current_time

                # Retrieve student details from the database
                cursor.execute("SELECT name, class, qr_valid_after FROM qr_data WHERE student_id = ?", (student_id,))
                student = cursor.fetchone()

                if student:
                    name, class_name, valid_after = student

                    # Handle case where `qr_valid_after` is NULL (i.e., first-time QR code generation)
                    if valid_after is None:
                        valid_after = "1970-01-01 00:00:00"  # Default to a very old date

                    # Convert timestamps to datetime objects before comparison
                    scanned_time_obj = datetime.datetime.strptime(scanned_timestamp, "%Y-%m-%d %H:%M:%S")
                    valid_after_obj = datetime.datetime.strptime(valid_after, "%Y-%m-%d %H:%M:%S")

                    # Reject outdated QR codes
                    if scanned_time_obj < valid_after_obj:
                        print(f"❌ QR code for {student_id} is outdated. Access denied.")
                        continue

                    # Get formatted timestamp for this scan
                    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Update last_scan_time in the database
                    cursor.execute("UPDATE qr_data SET last_scan_time = ? WHERE student_id = ?",
                                   (scan_time, student_id))
                    conn.commit()

                    print(f"📸 Scanned Student ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}")

                    # Display detected student info on the frame
                    cv2.putText(frame, f"ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}",
                                (qr_code.rect.left, qr_code.rect.top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # Update QR code (only if cooldown allows it)
                    update_qr_code(conn, cursor, student_id)

                    # Wait a short time to ensure the new QR code is in effect
                    print(f"⏳ Waiting {cooldown_period} seconds to ensure the new QR code is in effect...")
                    time.sleep(cooldown_period)

                else:
                    print("❌ Student not found in database.")

        # Show webcam feed with potential QR code overlays
        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # End feed and close resources
    webcam.release()
    cv2.destroyAllWindows()
    conn.close()


if __name__ == '__main__':
    webcam_index = set_webcam_index(1)
    main(webcam_index)
