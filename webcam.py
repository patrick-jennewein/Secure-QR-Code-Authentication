def set_webcam_index(index):
    DEFAULT_WEB_CAM = 0
    EXTERNAL_WEB_CAM = 1
    if index == 0:
        return DEFAULT_WEB_CAM
    elif index == 1:
        return EXTERNAL_WEB_CAM
