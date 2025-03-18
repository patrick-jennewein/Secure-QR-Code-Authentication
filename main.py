import cv2
from webcam import set_webcam_index

def main(webcam_index):
    # open connection to webcam and ensure opened succesfully
    webcam = cv2.VideoCapture(webcam_index)
    if not webcam.isOpened():
        print("Error: Could not open webcam.")
        exit()

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

if __name__ == '__main__':
    webcam_index = set_webcam_index(1)
    main(webcam_index)
