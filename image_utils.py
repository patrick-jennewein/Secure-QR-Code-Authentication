import cv2
from pyzbar.pyzbar import decode
import datetime
import sys
import numpy as np
import os
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


def detect_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    return faces


def save_scan_image(frame, student_id):
    """Save an image of the scanned frame with timestamp and ID, and return path."""
    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    filename = f"{student_id}_{timestamp}.jpg"
    filepath = os.path.join("scanned_images", filename)

    os.makedirs("scanned_images", exist_ok=True)
    cv2.imwrite(filepath, frame)

    return filepath


def safe_decode(frame):
    old_stderr = suppress_stderr()
    try:
        # First attempt: decode raw frame
        qr_codes = decode(frame)
        if qr_codes:
            return qr_codes

        # --- Enhanced pipeline ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        # CLAHE to boost contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Gradient magnitude (glare tends to show up as sharp changes)
        sobelx = cv2.Sobel(enhanced, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(enhanced, cv2.CV_64F, 0, 1, ksize=5)
        gradient_mag = np.sqrt(sobelx**2 + sobely**2)
        gradient_mag = np.uint8(np.clip(gradient_mag, 0, 255))

        # Suppress reflections by subtracting gradients
        reflection_reduced = cv2.subtract(enhanced, gradient_mag)

        # Sharpen the result
        sharpen_kernel = np.array([[0, -1, 0],
                                   [-1, 5, -1],
                                   [0, -1, 0]])
        sharpened = cv2.filter2D(reflection_reduced, -1, sharpen_kernel)

        # Decode
        processed = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        qr_codes = decode(processed)

    finally:
        restore_stderr(old_stderr)
    return qr_codes

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


