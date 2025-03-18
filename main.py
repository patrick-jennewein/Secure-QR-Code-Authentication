import cv2
import csv
import sqlite3


def set_webcam_index(index):
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM


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
        read, feed = webcam.read()
        if not read:
            print("Error: Could not read frame.")
            break
        cv2.imshow("Webcam Feed", feed)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # end feed
    webcam.release()
    cv2.destroyAllWindows()
    conn.close()


if __name__ == '__main__':
    webcam_index = set_webcam_index(1)
    main(webcam_index)
