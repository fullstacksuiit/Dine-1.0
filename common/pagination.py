from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def paginate_queryset(queryset, request, serializer_class):
    """
    Opt-in pagination helper for custom APIViews.

    If ?page= is present in the request, returns (pagination_meta, serialized_data).
    If ?page= is absent, returns (None, serialized_data) with all records (backward compatible).
    """
    page = request.query_params.get('page')
    if not page:
        return None, serializer_class(queryset, many=True).data

    paginator = StandardPagination()
    page_data = paginator.paginate_queryset(queryset, request)
    serialized = serializer_class(page_data, many=True).data
    pagination_meta = {
        'count': paginator.page.paginator.count,
        'num_pages': paginator.page.paginator.num_pages,
        'current_page': paginator.page.number,
        'page_size': paginator.get_page_size(request),
        'next': paginator.get_next_link(),
        'previous': paginator.get_previous_link(),
    }
    return pagination_meta, serialized
