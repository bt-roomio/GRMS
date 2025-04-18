from typing import Literal

from django.db.models import Avg, Count, Max, Min, Sum

AGGREGATION_FUNCTIONS = {
    "Min": Min,
    "Max": Max,
    "Avg": Avg,
    "Sum": Sum,
    "Count": Count,
    "Change": "Change",
    "None": None,  # Special case for no aggregation
}


IntervalUnit = Literal[
    "year",
    "week",
    "day",
    "hour",
    "minute",
    "second",
    "millisecond",
]

INTERVALS: dict[IntervalUnit, str] = {
    "week": "1 week",
    "day": "1 day",
    "hour": "1 hour",
    "minute": "1 minute",
    "second": "1 second",
    "millisecond": "1 millisecond",
}


def make_interval(n: int = 1, unit: IntervalUnit = "day") -> str:
    return f"{n} {unit}"
