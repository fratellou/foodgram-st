from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import (
    IngredientSerializer,
    UserSerializer,
    UserCreateSerializer,
    SubscribeSerializer
)
from recipes.models import Ingredient
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from users.models import Subscribe
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly

User = get_user_model()


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


class UserViewSet(DjoserUserViewSet):
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'error': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Subscribe.objects.filter(user=user, author=author).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscribe.objects.create(user=user, author=author)
            serializer = SubscribeSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # DELETE method
        subscription = Subscribe.objects.filter(user=user, author=author)
        if not subscription.exists():
            return Response(
                {'error': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscribed_authors = User.objects.filter(
            authors__user=request.user
        )
        page = self.paginate_queryset(subscribed_authors)
        serializer = SubscribeSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['put', 'delete'],
            permission_classes=[IsAuthenticated])
    def avatar(self, request, id=None):
        user = request.user
        if id != str(user.id):
            return Response(
                {'error': 'Вы можете изменять только свой аватар'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'DELETE':
            if not user.avatar:
                return Response(
                    {'error': 'Аватар отсутствует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.avatar.delete()
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PUT method
        if 'avatar' not in request.data:
            return Response(
                {'error': 'Отсутствует файл аватара'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.avatar = request.data['avatar']
        user.save()
        return Response(
            {'avatar': user.avatar.url},
            status=status.HTTP_200_OK
        )
