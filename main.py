import cv2
import csv
import sqlite3
import qrcode
import os
from pyzbar.pyzbar import decode
import datetime
import time
from colorama import init, Fore
import warnings
import sys
import smtplib
import mimetypes
from email.message import EmailMessage
from secure import sender_email, SENDER_PASSWORD, recipient_email


def send_email(student_id, student_name, class_name, new_timestamp, qr_code_path):
    """Sends an email with the QR code attached to a fixed email address."""

    # Create the email
    msg = EmailMessage()
    msg["Subject"] = f"New QR Code for {student_name} ({student_id})"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content(f"Hello,\n\nA new QR code has been generated for {student_name} ({student_id}). Please find it attached.\n\nBest,\nQR Authentication System")

    # Attach the QR code image
    with open(qr_code_path, "rb") as f:
        file_data = f.read()
        file_type = mimetypes.guess_type(qr_code_path)[0] or "application/octet-stream"
        msg.add_attachment(file_data, maintype=file_type.split('/')[0], subtype=file_type.split('/')[1], filename=f"QR_{student_id}.png")

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, SENDER_PASSWORD)
            server.send_message(msg)
        print(Fore.CYAN + f"{'Emailed':<10}{student_id:<8}{student_name:<30}{class_name:<10}{new_timestamp:<40}" + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"Error sending email: {e}" + Fore.RESET)


def suppress_stderr():
    sys.stderr.flush()
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    return old_stderr

def restore_stderr(old_stderr):
    sys.stderr.flush()
    os.dup2(old_stderr, 2)
    os.close(old_stderr)


def safe_decode(frame):
    old_stderr = suppress_stderr()
    try:
        qr_codes = decode(frame)
    finally:
        restore_stderr(old_stderr)
    return qr_codes

def set_webcam_index(index):
    """Sets the index of the webcam that will be used for this application"""
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM


def generate_qr_code(student_id, name, class_name, folder_path, initial):
    """generates a unique QR code"""

    # gather information about the QR code
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qr_data = f"ID:{student_id}|Name:{name}|Class:{class_name}|TS:{timestamp}"

    # ensure the folder where QR codes are stored actually exists
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(Fore.GREEN + f"Created folder: {folder_path}" + Fore.RESET)
        except OSError as e:
            print(Fore.RED +f"Error creating folder {folder_path}: {e}" + Fore.RESET)
            return None, None

    # save the new QR code image
    qr = qrcode.make(qr_data)
    qr_filename = os.path.join(folder_path, f"{student_id}.png")
    qr.save(qr_filename, format="PNG")

    # Convert QR code to binary and return
    with open(qr_filename, "rb") as f:
        qr_binary = f.read()

    return qr_binary, timestamp


def update_qr_code(conn, cursor, student_id):
    """updates a QR code and invalidates previous QR codes."""
    # query the database
    cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()

    # if the student is found in the database
    if student:
        name, class_name = student

        # generate a new QR code and get a new timestamp
        qr_code_binary, new_timestamp = generate_qr_code(student_id, name, class_name, "qr_codes", False)

        # update database with the new QR code and set valid timestamp
        cursor.execute("UPDATE qr_data SET qr_code = ?, qr_valid_after = ? WHERE student_id = ?",
                       (qr_code_binary, new_timestamp, student_id))
        conn.commit()
        print(f"{'Updated':<10}{student_id:<8}{name:<30}{class_name:<10}{new_timestamp:<40}")

        qr_code_path = os.path.join("qr_codes", f"{student_id}.png")  # Path to the saved QR code
        send_email(student_id, name, class_name, new_timestamp, qr_code_path)
    else:
        print(Fore.RED + f"ERROR: Student ID {student_id} not found." + Fore.RESET)


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


def main(webcam_index, folder_path, database_name):
    print(f"{'Status':<10}{'ID':<8}{'Name':<30}{'Class':<10}{'Timestamp':<40}")
    # open connection to webcam
    webcam = cv2.VideoCapture(webcam_index)
    if not webcam.isOpened():
        print(Fore.RED + f"Error: Could not open webcam" + Fore.RESET)
        exit()

    # initialize database
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    initialize_database(conn, cursor)

    # Ensure the folder exists before generating any QR codes
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            print(Fore.GREEN + f"Created folder {folder_path}" + Fore.RESET)
        except OSError as e:
            print(Fore.RED + f"Error creating folder {folder_path}: {e}" + Fore.RESET)
            exit()

    # Generate initial QR codes if needed
    generate_and_store_initial_qr_codes(cursor, "qr_codes")

    # Dictionary to track recent scans and prevent duplicate processing
    recent_scans = {}

    # capture webcam frames
    while True:
        read, frame = webcam.read()
        if not read:
            print(Fore.RED + "Error: Could not read frame." + Fore.RESET)
            break

        # detect and decodes QR codes from each frame
        qr_codes = safe_decode(frame)
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode("utf-8")

            if qr_data.startswith("ID:"):
                qr_data_dict = {}

                # QR code data into a dictionary
                for part in qr_data.split("|"):
                    key_value = part.split(":", 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        qr_data_dict[key.strip()] = value.strip()

                # ensure required fields exist
                if "ID" not in qr_data_dict or "TS" not in qr_data_dict:
                    print(Fore.RED + f"Invalid QR code format. Skipping..." + Fore.RESET)
                    continue

                student_id = qr_data_dict["ID"]
                scanned_timestamp = qr_data_dict["TS"]

                # get current time
                current_time = time.time()
                cooldown_period = 1.5

                # check if this student ID was scanned recently
                if student_id in recent_scans:
                    time_since_last_scan = current_time - recent_scans[student_id]
                    if time_since_last_scan < cooldown_period:
                        continue

                # update recent scan timestamp if have waited until after cooldown period
                recent_scans[student_id] = current_time

                # Retrieve student details from the database
                cursor.execute("SELECT name, class, qr_valid_after FROM qr_data WHERE student_id = ?", (student_id,))
                student = cursor.fetchone()

                if student:
                    name, class_name, valid_after = student

                    # handle edge case where `qr_valid_after` is NULL
                    if valid_after is None:
                        valid_after = "1970-01-01 00:00:00"

                    # convert timestamps for comparison
                    scanned_time_obj = datetime.datetime.strptime(scanned_timestamp, "%Y-%m-%d %H:%M:%S")
                    valid_after_obj = datetime.datetime.strptime(valid_after, "%Y-%m-%d %H:%M:%S")

                    # reject outdated QR codes
                    if scanned_time_obj < valid_after_obj:
                        outdated_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(Fore.RED + f"{'Outdated':<10}{student_id:<8}{name:<30}{class_name:<10}{outdated_time:<40}" + Fore.RESET)
                        continue

                    # get formatted timestamp for valid scan and update database
                    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("UPDATE qr_data SET last_scan_time = ? WHERE student_id = ?",
                                   (scan_time, student_id))
                    conn.commit()

                    print(Fore.GREEN + f"{'Success':<10}{student_id:<8}{name:<30}{class_name:<10}{scan_time:<40}" + Fore.RESET)

                    # display detected student info on the frame
                    cv2.putText(frame, f"ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}",
                                (qr_code.rect.left, qr_code.rect.top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # update QR code
                    update_qr_code(conn, cursor, student_id)

                    # Wait a short time to ensure the new QR code is in effect
                    # print(f"Waiting {cooldown_period} seconds to ensure the new QR code is in effect...")
                    time.sleep(cooldown_period)

                else:
                    print(Fore.RED + "Student not found in database." + Fore.RESET)

        # Show webcam feed with potential QR code overlays
        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # End feed and close resources
    webcam.release()
    cv2.destroyAllWindows()
    conn.close()


if __name__ == '__main__':
    webcam_index = set_webcam_index(0)
    qr_code_folder = "qr_codes"
    database_name = "students.db"
    main(webcam_index, qr_code_folder, database_name)
