from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Exists, OuterRef, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    Base64ImageField,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    ShoppingCartCountSerializer,
    SubscribeSerializer,
    UserCreateSerializer,
    UserSerializer,
    SubscribeCreateSerializer,
    FavoriteCreateSerializer,
    ShoppingCartCreateSerializer
)
from constants import PAGINATION_MAX_PAGE_SIZE, PAGINATION_PAGE_SIZE
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscribe

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = PAGINATION_PAGE_SIZE
    page_size_query_param = "limit"
    page_query_param = "page"
    max_page_size = PAGINATION_MAX_PAGE_SIZE


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [filters.SearchFilter]
    permission_classes = [AllowAny]
    search_fields = ["^name"]
    pagination_class = None


class UserViewSet(DjoserUserViewSet):
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True, methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == "POST":
            serializer = SubscribeCreateSerializer(
                data={"author": author.id},
                context={"request": request}
            )
            try:
                serializer.is_valid(raise_exception=True)
                subscription = serializer.save()
            except serializers.ValidationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription = Subscribe.objects.filter(
                user=request.user, author=author
            ).annotate(
                recipes_count=Count('author__recipes')
            ).first()

            response_serializer = SubscribeSerializer(
                subscription,
                context={"request": request},
            )
            return Response(response_serializer.data, status=201)

        deleted_count, _ = Subscribe.objects.filter(
            user=user,
            author=author
        ).delete()

        if deleted_count == 0:
            return Response(
                {"error": "Вы не подписаны на этого пользователя"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = Subscribe.objects.filter(
            user=request.user
        ).annotate(
            recipes_count=Count('author__recipes')
        )
        page = self.paginate_queryset(subscriptions)
        serializer = SubscribeSerializer(
            page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=["put", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request, id=None):
        if id == "me":
            user = request.user
        else:
            try:
                user = User.objects.get(id=id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Пользователь не найден"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if user != request.user:
            return Response(
                {"error": "Вы можете изменять только свой аватар"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == "DELETE":
            if not user.avatar:
                return Response(
                    {"error": "Аватар отсутствует"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.avatar.delete()
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if "avatar" not in request.data or not request.data["avatar"]:
            return Response(
                {"error": "Отсутствует файл аватара"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer = Base64ImageField()
            avatar_file = serializer.to_internal_value(request.data["avatar"])
            serializer.validate(avatar_file)
            user.avatar = avatar_file
            user.save()
            return Response({"avatar": user.avatar.url},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Ошибка при сохранении файла: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related("author").prefetch_related(
        "recipe_ingredients__ingredient"
    )
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeSerializer
        return RecipeCreateSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAuthorOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "recipe_ingredients__ingredient"
        )

        if user.is_authenticated:
            favorite_subquery = Favorite.objects.filter(
                user=user,
                recipe=OuterRef('pk')
            )
            cart_subquery = ShoppingCart.objects.filter(
                user=user,
                recipe=OuterRef('pk')
            )
            queryset = queryset.annotate(
                is_favorited=Exists(favorite_subquery),
                is_in_shopping_cart=Exists(cart_subquery)
            )
        else:
            queryset = queryset.annotate(
                is_favorited=models.Value(
                    False, output_field=models.BooleanField()),
                is_in_shopping_cart=models.Value(
                    False, output_field=models.BooleanField())
            )

        author_id = self.request.query_params.get("author")
        if author_id:
            queryset = queryset.filter(author__id=author_id)

        is_favorited = self.request.query_params.get("is_favorited")
        if is_favorited == "1" and user.is_authenticated:
            queryset = queryset.filter(favorites__user=user)

        return queryset

    @action(
        detail=True, methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            serializer = FavoriteCreateSerializer(
                data={"recipe": recipe.id},
                context={"request": request}
            )
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
            except serializers.ValidationError as e:
                return Response(
                    {"errors": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response_serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)

        deleted_count, _ = Favorite.objects.filter(
            user=user,
            recipe=recipe
        ).delete()

        if deleted_count == 0:
            return Response(
                {"errors": "Рецепта нет в избранном."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def favorites(self, request):
        favorite_recipes = self.get_queryset().filter(is_favorited=True)

        page = self.paginate_queryset(favorite_recipes)
        if page is not None:
            serializer = RecipeSerializer(
                page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = RecipeSerializer(
            favorite_recipes, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def shopping_cart_list(self, request):
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        serializer = ShoppingCartCountSerializer(shopping_cart, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def shopping_cart_count(self, request):
        count = ShoppingCart.objects.filter(user=request.user).count()
        return Response({"count": count})

    @action(
        detail=True, methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            serializer = ShoppingCartCreateSerializer(
                data={"recipe": recipe.id},
                context={"request": request}
            )

            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
            except serializers.ValidationError as e:
                return Response(
                    {"errors": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            count = ShoppingCart.objects.filter(user=user).count()
            return Response({"count": count}, status=status.HTTP_201_CREATED)

        deleted_count, _ = ShoppingCart.objects.filter(
            user=user,
            recipe=recipe
        ).delete()

        if deleted_count == 0:
            return Response(
                {"errors": "Рецепта нет в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        count = ShoppingCart.objects.filter(user=user).count()
        return Response({"count": count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_carts__user=request.user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        shopping_list = ["Список покупок:\n"]
        for item in ingredients:
            shopping_list.append(
                f"{item['ingredient__name']} - "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}\n"
            )

        response = HttpResponse("".join(shopping_list),
                                content_type="text/plain")
        response["Content-Disposition"] = 'attachment;' + \
            'filename="shopping_list.txt"'
        return response

    @action(methods=["get"], detail=True, url_path="get-link")
    def get_link(self, request, pk=None):
        try:
            recipe = self.get_object()
            return Response(
                {
                    "short-link": request.build_absolute_uri(
                        reverse("api:recipes-detail", kwargs={"pk": recipe.pk})
                    )
                },
                status=HTTPStatus.OK,
            )
        except Http404:
            raise NotFound(detail="Страница не найдена.")

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", True)
            instance = self.get_object()

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)

        except serializers.ValidationError as e:
            return Response({"errors": e.detail},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Ошибка сервера: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_update(self, serializer):
        serializer.save()
