def set_webcam_index(index):
    """Sets the index of the webcam that will be used for this application"""
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM