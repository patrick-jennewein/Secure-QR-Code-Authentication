import cv2
import csv
import sqlite3
import qrcode
import io
import os
from pyzbar.pyzbar import decode


def set_webcam_index(index):
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM


def generate_qr_code(student_id, name, class_name):
    """generates a unique QR code for a student and returns it as binary data."""
    qr_data = f"ID:{student_id}|Name:{name}|Class:{class_name}"
    qr = qrcode.make(qr_data)

    # Ensure the qr_codes folder exists
    folder_path = "qr_codes"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save the QR code as an image file named after the student ID
    qr_filename = os.path.join(folder_path, f"{student_id}.png")
    qr.save(qr_filename, format="PNG")

    # Convert QR code to binary data
    qr_bytes = io.BytesIO()
    qr.save(qr_bytes, format="PNG")
    return qr_bytes.getvalue()  # Return binary representation of QR code

def generate_and_store_initial_qr_codes(cursor):
    """Generates and stores QR codes for all students when initially creating the table."""
    cursor.execute("SELECT student_id, name, class FROM qr_data WHERE qr_code IS NULL")
    students = cursor.fetchall()

    for student_id, name, class_name in students:
        qr_code_binary = generate_qr_code(student_id, name, class_name)
        cursor.execute("UPDATE qr_data SET qr_code = ? WHERE student_id = ?", (qr_code_binary, student_id))


def update_qr_code_for_student(cursor, student_id):
    """Updates a student's QR code when scanned, creating a new one."""
    cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()

    if student:
        name, class_name = student
        qr_code_binary = generate_qr_code(student_id, name, class_name)
        cursor.execute("UPDATE qr_data SET qr_code = ? WHERE student_id = ?", (qr_code_binary, student_id))
        print(f"QR code updated for student {student_id}")
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
    # open connection to webcam and ensure opened successfully
    webcam = cv2.VideoCapture(webcam_index)
    if not webcam.isOpened():
        print("Error: Could not open webcam.")
        exit()

    # initialize database
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    initialize_database(conn, cursor)

    # capture webcam by frame
    while True:
        read, frame = webcam.read()
        if not read:
            print("Error: Could not read frame.")
            break

        # Decode QR codes from the frame
        qr_codes = decode(frame)
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode("utf-8")

            if qr_data.startswith("ID:"):
                student_id = qr_data.split("|")[0].split(":")[1]

                # Query the database for student info
                cursor.execute("SELECT name, class FROM qr_data WHERE student_id = ?", (student_id,))
                student = cursor.fetchone()

                if student:
                    name, class_name = student
                    print(f"Student ID: {student_id}, Name: {name}, Class: {class_name}")

                    # Display detected student info on the frame
                    cv2.putText(frame, f"ID: {student_id}, Name: {name}, Class: {class_name}",
                                (qr_code.rect.left, qr_code.rect.top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                else:
                    print("Student not found in database.")

        # Show webcam feed with potential QR code overlays
        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # end feed
    webcam.release()
    cv2.destroyAllWindows()
    conn.close()


if __name__ == '__main__':
    webcam_index = set_webcam_index(1)
    main(webcam_index)
