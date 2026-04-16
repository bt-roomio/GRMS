import time
from calendar import monthrange
from datetime import date, datetime
from datetime import timezone as tz

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
    """
    Convert a datetime object to a Unix timestamp (seconds since epoch).
    """
    return time.mktime(date_time.timetuple())


def datetime_to_unix(date_time):
    """
    Convert a datetime object or ISO format string to a Unix timestamp (seconds since epoch).

    Args:
        date_time (datetime or str): A datetime object (can be timezone-aware or naive)
                                     or an ISO format datetime string.

    Returns:
        int: Unix timestamp in seconds.
    """
    # If input is a string, parse it first
    if isinstance(date_time, str):
        date_time = datetime.fromisoformat(date_time.replace("Z", "+00:00"))

    # Handle datetime objects
    if isinstance(date_time, datetime):
        if date_time.tzinfo is None:
            # If naive datetime, assume UTC
            date_time = date_time.replace(tzinfo=tz.utc)

        return int(date_time.timestamp())

    raise ValueError(f"Input must be a datetime object or ISO format string, got {type(date_time)}")


def unix_to_datetime(timestamp):
    """
    Convert a Unix timestamp (seconds or milliseconds) to a timezone-aware datetime object in UTC.

    Args:
        timestamp (int, float, or str): Unix timestamp in seconds (10-digit) or milliseconds (13-digit).
    Returns:
        datetime: Timezone-aware datetime in UTC.
    """
    ts = float(timestamp)

    if ts > 1e10:
        ts /= 1000.0

    return datetime.fromtimestamp(ts, tz=tz.utc)


def convert_datetime(input_value):
    """
    Convert a dynamic datetime input (either a datetime string or a Unix timestamp)
    to a string in the format "YYYY-MM-DD HH:MM:SS".

    Args:
        input_value (str, int, float, datetime.datetime): The datetime input. It can be:
            - A string of format "YYYY-MM-DD HH:MM:SS".
            - A string or number representing a Unix timestamp in milliseconds.
            - Optionally, a Unix timestamp in seconds.

    Returns:
        str: The formatted datetime string "YYYY-MM-DD HH:MM:SS".

    Raises:
        ValueError: If the input cannot be parsed as a valid datetime.
    """

    # If the input is already a datetime object, just format it.
    if isinstance(input_value, datetime):
        return input_value.strftime("%Y-%m-%d %H:%M:%S")

    # If the input is an int or float, assume it's a Unix timestamp.
    if isinstance(input_value, (int, float)):
        timestamp = float(input_value)
        # Check if the timestamp is in milliseconds (length > 10 digits or value is high)
        if timestamp > 1e10:
            timestamp /= 1000.0
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # If the input is a string, check if it is a digit string or a datetime string.
    if isinstance(input_value, str):
        input_value = input_value.strip()
        # If the string is all digits, treat it as a timestamp.
        if input_value.isdigit():
            timestamp = float(input_value)
            # If the string length is more than 10 digits, assume it's milliseconds.
            if len(input_value) > 10:
                timestamp /= 1000.0
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Otherwise, try parsing it as a datetime string.
            try:
                dt = datetime.strptime(input_value, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError(f"Unrecognized datetime format for input: {input_value}")

    # If the input doesn't match any of the expected types, raise an error.
    raise ValueError("Input type must be a string, int, float, or datetime.datetime.")
