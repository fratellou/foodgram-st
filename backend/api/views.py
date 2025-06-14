from rest_framework import viewsets
from .serializers import IngredientSerializer
from recipes.models import Ingredient
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    page_query_param = "page"
    max_page_size = 50


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [AllowAny]
    search_fields = ['^name']
    pagination_class = None
