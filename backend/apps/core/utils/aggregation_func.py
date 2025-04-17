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

INTERVALS = {
    "year": "year",
    "month": "month",
    "week": "week",
    "day": "day",
    "hour": "hour",
    "minute": "minute",
    "second": "second",
    "milliseconds": "milliseconds",
}
