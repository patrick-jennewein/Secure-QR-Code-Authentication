import qrcode
import datetime
from colorama import Fore
import os
from email_utils import send_email


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


def update_qr_code(conn, cursor, student_id, image_path=None):
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
        send_email(student_id, name, class_name, new_timestamp, qr_code_path, image_path=image_path)
    else:
        print(Fore.RED + f"ERROR: Student ID {student_id} not found." + Fore.RESET)
