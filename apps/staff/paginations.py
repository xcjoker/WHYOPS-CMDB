from rest_framework.pagination import PageNumberPagination


class StaffPagination(PageNumberPagination):
    page_query_param = "page"  # 在url中指定显示第几页 ?page=
    page_size_query_param = "size"  # 可以在url中指定每一页要多少条数据 ?page=
    page_size = 2
