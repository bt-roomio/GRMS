from typing import List
from django.db.models import QuerySet, Window, F, Subquery
from django.db.models.functions import RowNumber


def remove_duplicate_rows(queryset: QuerySet, columns: List[str]):
    subquery = (
        queryset.annotate(
            row_num=Window(
                expression=RowNumber(),
                partition_by=[F(column) for column in columns],
                order_by=F("id").asc(),
            )
        )
        .filter(row_num__gt=1)
        .values("id")
    )

    data = queryset.filter(id__in=Subquery(subquery))
    return len(data)  # .delete()
