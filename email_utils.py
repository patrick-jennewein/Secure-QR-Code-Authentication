from colorama import init, Fore
import smtplib
import mimetypes
from email.message import EmailMessage
from secure import sender_email, SENDER_PASSWORD, recipient_email
import os

def send_email(student_id, student_name, class_name, new_timestamp, qr_code_path, image_path=None):
    """Sends an email with the QR code and optionally the scanned image."""

    msg = EmailMessage()
    msg["Subject"] = f"New QR Code for {student_name} ({student_id})"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello,\n\nA new QR code has been generated for {student_name} ({student_id}). "
        f"Attached are the QR code and the image captured at the time of scan.\n\nBest,\nQR Authentication System"
    )

    # Attach QR code
    with open(qr_code_path, "rb") as f:
        file_data = f.read()
        file_type = mimetypes.guess_type(qr_code_path)[0] or "application/octet-stream"
        msg.add_attachment(file_data, maintype=file_type.split('/')[0],
                           subtype=file_type.split('/')[1], filename=f"QR_{student_id}.png")

    # Attach scanned image if available
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
            msg.add_attachment(image_data, maintype=image_type.split('/')[0],
                               subtype=image_type.split('/')[1], filename=os.path.basename(image_path))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, SENDER_PASSWORD)
            server.send_message(msg)
        print(Fore.CYAN + f"{'Emailed':<10}{student_id:<8}{student_name:<30}{class_name:<10}{new_timestamp:<40}" + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"Error sending email: {e}" + Fore.RESET)

