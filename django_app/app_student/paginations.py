from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Har bir sahifada 10 ta yozuv
    page_size_query_param = 'page_size'
    max_page_size = 100