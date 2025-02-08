import time
from calendar import monthrange
from datetime import date, datetime

from django.utils import timezone

months = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def month_first_last_days(day=timezone.now()):
    _, last_day = monthrange(day.year, day.month)
    return date(day.year, day.month, 1), date(day.year, day.month, last_day)


def add_months(source_date, extra):
    """
    Source: https://stackoverflow.com/a/4131114/5407526
    """
    month = source_date.month - 1 + extra
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def get_weekday(date):
    return f"{date.weekday() + 1}_{date.strftime('%A').lower()}"


def datetime_unix(date_time: datetime):
    return time.mktime(date_time.timetuple())


def unix_datetime(timestamp: int):
    return datetime.fromtimestamp(timestamp)
