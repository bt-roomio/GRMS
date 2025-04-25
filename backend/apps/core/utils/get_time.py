import time
from datetime import datetime


def get_mil_sec():
    return int(time.time() * 1000)


def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
