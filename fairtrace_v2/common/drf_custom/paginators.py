from rest_framework import pagination


class LargePaginator(pagination.PageNumberPagination):
    """Class to handle LargePaginator and functions."""

    page_size = 999
