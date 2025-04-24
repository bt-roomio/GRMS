from datetime import datetime


def get_mil_sec():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
