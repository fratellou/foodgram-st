from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, UserViewSet

app_name = 'api'

router = DefaultRouter()
router.register(
    r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
