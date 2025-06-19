from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from users.models import User


class Ingredient(models.Model):
    NAME_MAX_LENGTH = 128
    MEASUREMENT_MAX_LENGTH = 64

    name = models.CharField(max_length=NAME_MAX_LENGTH, unique=True,
                            verbose_name="Название")
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_MAX_LENGTH, verbose_name="Единица измерения")

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    NAME_MAX_LENGTH = 128
    IMAGE_UPLOAD_TO = "recipes/"

    author = models.ForeignKey(
        User, verbose_name="Автор", on_delete=models.CASCADE,
        related_name="recipes"
    )
    name = models.CharField(max_length=NAME_MAX_LENGTH,
                            verbose_name="Название")
    image = models.ImageField(
        verbose_name="Картинка", upload_to=IMAGE_UPLOAD_TO
    )
    text = models.CharField(verbose_name="Описание")
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name="Список ингредиентов",
        through="RecipeIngredient",
        related_name="recipes",
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления (в минутах)",
        validators=[
            MinValueValidator(
                1, message="Время должно быть не менее 1 минуты"),
            MaxValueValidator(1440,
                              message="Время не должно превышать"
                              + "24 часа (1440 минут)")],
    )

    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        default=timezone.now,
        db_index=True
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="Ингредиент",
        on_delete=models.CASCADE,
        related_name="ingredient_recipe",
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Колличество ингредиента в рецепте",
        validators=[
            MinValueValidator(
                1, message="Количество ингредиентов должно быть не менее 1"),
            MaxValueValidator(
                100, message="Количество ингредиентов не должно превышать 100")
        ],
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient"
            )
        ]

    def __str__(self):
        return (
            f"{self.recipe.name}: "
            f"{self.ingredient.name} - "
            f"{self.amount} "
            f"{self.ingredient.measurement_unit}"
        )


class BaseUserRecipeModel(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        'Recipe',
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_%(class)s"
            )
        ]

    def __str__(self):
        return f"{self.user.username} в {self._meta.verbose_name}" + \
            f"{self.recipe.name}"


class Favorite(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        default_related_name = "favorites"


class ShoppingCart(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"
        default_related_name = "shopping_carts"
