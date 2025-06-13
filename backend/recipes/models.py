from django.db import models
from django.core.validators import MinValueValidator


class Ingredient(models.Model):
    name = models.CharField(max_length=128, unique=True,
                            verbose_name='Название')
    measurement_unit = models.CharField(
        max_length=64, unique=True, verbose_name='Единица измерения')

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    # author =
    name = models.CharField(max_length=128, verbose_name='Название')
    image = models.ImageField(verbose_name='Картинка',
                              upload_to='recipes/images/')
    text = models.CharField(verbose_name='Описание')
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name='Список ингредиентов',
        through='Recipe_Ingredient')
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления (в минутах)',
        validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class Recipe_Ingredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, verbose_name='Рецепт', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(
        Ingredient, verbose_name='Ингредиент', on_delete=models.CASCADE)
    amount = models.IntegerField(
        verbose_name='Колличество ингредиента в рецепте',
        validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Ингридиент в рецепте'
        verbose_name_plural = 'Ингридиенты в рецепте'

    def __str__(self):
        return (f'{self.recipe.name}: '
                f'{self.ingredient.name} - '
                f'{self.amount} '
                f'{self.ingredient.measurement_unit}')
