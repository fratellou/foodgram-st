from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet

app_name = 'api'

router = DefaultRouter()
router.register(
    r'ingredients', IngredientViewSet, basename='ingredients')


urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
