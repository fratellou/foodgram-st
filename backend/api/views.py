from http import HTTPStatus
from io import BytesIO

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
    FavoriteCreateSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    ShoppingCartCountSerializer,
    ShoppingCartCreateSerializer,
    SubscribeCreateSerializer,
    SubscribeSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from constants import (
    DOWNLOAD_SHOPPING_CART_FILE_NAME,
    PAGINATION_MAX_PAGE_SIZE,
    PAGINATION_PAGE_SIZE,
)
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
            user = get_object_or_404(User, id=id)

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

    def _handle_relation_action(self, request, pk,
                                relation_model, create_serializer,
                                error_message, return_count=False):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            serializer = create_serializer(
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

            if return_count:
                count = relation_model.objects.filter(user=user).count()
                return Response({"count": count},
                                status=status.HTTP_201_CREATED)

            response_serializer = RecipeShortSerializer(
                recipe, context={"request": request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)

        deleted_count, _ = relation_model.objects.filter(
            user=user,
            recipe=recipe
        ).delete()

        if deleted_count == 0:
            return Response(
                {"errors": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if return_count:
            count = relation_model.objects.filter(user=user).count()
            return Response({"count": count}, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self._handle_relation_action(
            request=request,
            pk=pk,
            relation_model=Favorite,
            create_serializer=FavoriteCreateSerializer,
            error_message="Рецепта нет в избранном."
        )

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
        return self._handle_relation_action(
            request=request,
            pk=pk,
            relation_model=ShoppingCart,
            create_serializer=ShoppingCartCreateSerializer,
            error_message="Рецепта нет в списке покупок.",
            return_count=True
        )

    @staticmethod
    def generate_shopping_list(user):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_carts__user=user
            )
            .values(
                "ingredient__name",
                "ingredient__measurement_unit"
            )
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        content = BytesIO()
        content.write("Список покупок:\n".encode('utf-8'))

        for item in ingredients:
            line = (
                f"{item['ingredient__name']} - "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}\n"
            )
            content.write(line.encode('utf-8'))
        content.seek(0)
        filename = DOWNLOAD_SHOPPING_CART_FILE_NAME
        return filename, content

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        filename, content = self.generate_shopping_list(request.user)
        response = HttpResponse(
            content,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
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
