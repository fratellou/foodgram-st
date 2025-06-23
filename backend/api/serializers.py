import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django_filters import rest_framework as filters
from djoser.serializers import UserSerializer
from rest_framework import serializers

from foodgram.constants import COOKING_MIN_VALUE, MAX_IMAGE_SIZE
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscribe

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)

    def validate(self, value):
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError(
                ('Размер файла не должен превышать'
                 f'{self.MAX_IMAGE_SIZE//(1024*1024)}MB')
            )

        valid_extensions = ('jpg', 'jpeg', 'png', 'gif')
        ext = value.name.split('.')[-1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                ('Неподдерживаемый формат файла.'
                 f'Допустимые форматы: {", ".join(valid_extensions)}')
            )

        return value


class UserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscribe.objects.filter(user=request.user,
                                            author=obj).exists()
        return False


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
            'email': {'required': True, 'allow_blank': False},
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
        )
        return user

    def to_representation(self, instance):
        return {
            'email': instance.email,
            'id': instance.id,
            'username': instance.username,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredients')
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(min_value=COOKING_MIN_VALUE)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, attrs):
        ingredients = self.initial_data.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError(
                'Необходим хотя бы один ингредиент')

        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться')

        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if len(existing_ingredients) != len(ingredient_ids):
            raise serializers.ValidationError(
                'Указаны несуществующие ингредиенты')

        return attrs

    def create_ingredients(self, recipe, ingredients):
        recipe.recipe_ingredients.all().delete()

        return RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe, ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user
        recipe = super().create(validated_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(instance, ingredients_data)

        return super().update(instance, validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        return RecipeShortSerializer(instance.recipe).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        return RecipeShortSerializer(instance.recipe).data


class SubscribeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    avatar = serializers.ImageField(source='author.avatar', read_only=True)

    class Meta:
        model = Subscribe
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
            'recipes',
            'recipes_count',
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.author.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]
        return RecipeShortSerializer(
            recipes, many=True, context={'request': request}
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True)
    image = Base64ImageField(required=True)
    author = UserSerializer(read_only=True)
    id = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'ingredients',
            'image',
            'name',
            'text',
            'cooking_time',
            'author',
        )
        extra_kwargs = {
            'ingredients': {'required': True, 'allow_blank': False},
            'name': {'required': True, 'allow_blank': False},
            'text': {'required': True, 'allow_blank': False},
            'image': {'required': True, 'allow_blank': False},
            'cooking_time': {'required': True},
        }

    def validate(self, data):
        if 'cooking_time' in data and data['cooking_time'] <= 0:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0'
            )

        if 'ingredients' in data:
            ingredients = data['ingredients']
            ingredient_ids = [ingredient['id'] for ingredient in ingredients]

            if len(ingredient_ids) != len(set(ingredient_ids)):
                raise serializers.ValidationError(
                    'Ингредиенты должны быть уникальны.')

            for ingredient in ingredients:
                if int(ingredient.get('amount', 0)) <= 0:
                    raise serializers.ValidationError(
                        'Количество ингредиента должно быть больше 0'
                    )

        return data

    @transaction.atomic
    def create_ingredients(self, recipe, ingredients_data):
        ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount'],
            )
            for ingredient in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients)

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user, **validated_data
        )
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class ShoppingCartCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('id',)

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': instance.recipe.image.url if
            instance.recipe.image else None,
            'cooking_time': instance.recipe.cooking_time,
        }


class BaseUserRelationCreateSerializer(serializers.ModelSerializer):
    error_message = None
    relation_field = None

    def create(self, validated_data):
        return self.Meta.model.objects.create(
            user=self.context['request'].user,
            **validated_data
        )

    def validate(self, data):
        if self.relation_field is None:
            raise NotImplementedError(
                'relation_field должны быть определены в подклассах')

        obj = data.get(self.relation_field)
        user = self.context['request'].user

        if self.Meta.model.objects.filter(
            user=user,
            **{self.relation_field: obj}
        ).exists():
            raise serializers.ValidationError(self.error_message)

        return data

    class Meta:
        abstract = True


class FavoriteCreateSerializer(BaseUserRelationCreateSerializer):
    relation_field = 'recipe'
    error_message = 'Рецепт уже в избранном'

    class Meta(BaseUserRelationCreateSerializer.Meta):
        model = Favorite
        fields = ('recipe',)


class ShoppingCartCreateSerializer(BaseUserRelationCreateSerializer):
    relation_field = 'recipe'
    error_message = 'Рецепт уже в корзине'

    class Meta(BaseUserRelationCreateSerializer.Meta):
        model = ShoppingCart
        fields = ('recipe',)


class SubscribeCreateSerializer(BaseUserRelationCreateSerializer):
    relation_field = 'author'
    error_message = 'Вы уже подписаны на этого пользователя'

    class Meta(BaseUserRelationCreateSerializer.Meta):
        model = Subscribe
        fields = ('author',)

    def validate_author(self, value):
        user = self.context['request'].user
        if user == value:
            raise serializers.ValidationError(
                'Нельзя подписаться на себя'
            )
        return value


class RecipeFilter(filters.FilterSet):
    author = filters.NumberFilter(field_name='author__id')
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_in_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_in_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_carts__user=user)
        return queryset
