from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


def pagination(queryset, serializer, page, size=15):
    page = page or 1
    offset = (page - 1) * size
    limit = offset + size
    serializer.instance = queryset[offset:limit]
    return {"count": queryset.count(), "results": serializer.data}


class PageSizePagination(LimitOffsetPagination):
    limit_query_param = "size"
    offset_query_param = "page"

    def get_offset(self, request) -> int:
        """
        Interpret the 'page' parameter as a page number and calculate the offset.
        """
        try:
            page_number = int(request.query_params.get(self.offset_query_param, 1))
        except (KeyError, ValueError):
            page_number = 1

        if page_number < 1:
            page_number = 1

        # Retrieve limit and ensure it's an integer
        limit = self.get_limit(request)
        if limit is None:
            limit = self.default_limit or 1
        if not isinstance(limit, int):
            limit = 10

        return (page_number - 1) * limit

    def get_paginated_response(self, data):
        """
        Return a response without the next and previous links.
        """
        return Response(
            {
                "count": self.count,
                "results": data,
            }
        )
