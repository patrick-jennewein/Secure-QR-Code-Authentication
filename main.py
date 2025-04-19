import cv2
import sqlite3
import datetime
import time
from colorama import Fore
import os
from sound_utils import play_sound
from image_utils import save_scan_image, safe_decode
from qr_utils import update_qr_code
from db_utils import initialize_database, generate_and_store_initial_qr_codes, log_scan_event
from config import qr_code_folder, database_name, cooldown_period
from webcam import set_webcam_index
from image_utils import detect_faces

def main(webcam_index, folder_path, database_name):
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
    print(f"{'Status':<10}{'ID':<8}{'Name':<30}{'Class':<10}{'Timestamp':<40}")
    while True:
        read, frame = webcam.read()
        if not read:
            print(Fore.RED + "Error: Could not read frame." + Fore.RESET)
            break

        # detect and decodes QR codes from each frame
        qr_codes = safe_decode(frame)
        faces = detect_faces(frame)

        # Draw face boxes for debug
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        if qr_codes and len(faces) > 0:
            for qr_code in qr_codes:
                qr_data = qr_code.data.decode("utf-8")
                print(qr_data)

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
                        play_sound(success=False)
                        continue

                    student_id = qr_data_dict["ID"]
                    scanned_timestamp = qr_data_dict["TS"]

                    # get current time
                    current_time = time.time()

                    # check if this student ID was scanned recently
                    if student_id in recent_scans:
                        time_since_last_scan = current_time - recent_scans[student_id]
                        if time_since_last_scan < cooldown_period:
                            continue

                    # update recent scan timestamp if have waited until after cooldown period
                    recent_scans[student_id] = current_time

                    # Retrieve student details from the database
                    cursor.execute("SELECT name, class, qr_valid_after FROM qr_data WHERE student_id = ?",
                                   (student_id,))
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
                            play_sound(success=False)
                            print(
                                Fore.RED + f"{'Outdated':<10}{student_id:<8}{name:<30}{class_name:<10}{outdated_time:<40}" + Fore.RESET)
                            log_scan_event("Outdated", student_id, name, class_name, outdated_time)
                            continue

                        # get formatted timestamp for valid scan and update database
                        scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("UPDATE qr_data SET last_scan_time = ? WHERE student_id = ?",
                                       (scan_time, student_id))
                        conn.commit()

                        print(
                            Fore.GREEN + f"{'Success':<10}{student_id:<8}{name:<30}{class_name:<10}{scan_time:<40}" + Fore.RESET)
                        play_sound(success=True)
                        image_path = save_scan_image(frame, student_id)
                        log_scan_event("Success", student_id, name, class_name, scan_time)

                        # display detected student info on the frame
                        cv2.putText(frame, f"ID: {student_id}, Name: {name}, Class: {class_name}, Time: {scan_time}",
                                    (qr_code.rect.left, qr_code.rect.top - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                        # update QR code
                        update_qr_code(conn, cursor, student_id, image_path=image_path)

                        # Wait a short time to ensure the new QR code is in effect
                        # print(f"Waiting {cooldown_period} seconds to ensure the new QR code is in effect...")
                        time.sleep(cooldown_period)

                    else:
                        print(Fore.RED + "Student not found in database." + Fore.RESET)
                        log_scan_event("Not found", student_id, name, class_name, scan_time)
                        play_sound(success=False)

        # else:
        #     print(Fore.YELLOW + "Skipping: QR or face missing." + Fore.RESET)

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
    main(webcam_index, qr_code_folder, database_name)
