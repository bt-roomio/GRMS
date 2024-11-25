from django.db.models import Avg, Count, Max, Min, Sum

AGGREGATION_FUNCTIONS = {
    "Min": Min,
    "Max": Max,
    "Avg": Avg,
    "Sum": Sum,
    "Count": Count,
    "None": None,  # Special case for no aggregation
}
