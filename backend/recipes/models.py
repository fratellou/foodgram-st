from django.core.validators import MinValueValidator
from django.db import models

from users.models import User


class Ingredient(models.Model):
    NAME_MAX_LENGTH = 128
    MEASUREMENT_MAX_LENGTH = 64

    name = models.CharField(max_length=NAME_MAX_LENGTH, unique=True,
                            verbose_name="Название")
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_MAX_LENGTH, verbose_name="Единица измерения")

    class Meta:
        ordering = ["name"]
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
        related_name="recipe",
    )
    cooking_time = models.IntegerField(
        verbose_name="Время приготовления (в минутах)",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="recipe_ingredient",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="Ингредиент",
        on_delete=models.CASCADE,
        related_name="ingredient_recipe",
    )
    amount = models.IntegerField(
        verbose_name="Колличество ингредиента в рецепте",
        validators=[MinValueValidator(1)],
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
        ordering = (
            "recipe",
            "ingredient",
        )

    def __str__(self):
        return (
            f"{self.recipe.name}: "
            f"{self.ingredient.name} - "
            f"{self.amount} "
            f"{self.ingredient.measurement_unit}"
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="favorite_user",
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="favorite_recipe",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_user_recipe_favorite"
            )
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.user.username} в избранном " f"{self.recipe.name}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="shopping_user",
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="shopping_recipe",
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_shopping_cart"
            )
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.user.username} в корзине " f"{self.recipe.name}"
