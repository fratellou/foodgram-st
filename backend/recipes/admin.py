from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    verbose_name = "Ингредиент"
    verbose_name_plural = "Ингредиенты"
    fields = ("ingredient", "amount")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "author",
        "favorites_count",
        "cooking_time",
        "image_preview",
    )
    search_fields = ("name", "author__username")
    list_filter = ("author",)
    inlines = [RecipeIngredientInline]
    readonly_fields = ("favorites_count",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('author').annotate(
            favorites_count_annotation=Count('favorites')
        )

    @admin.display(description="В избранном")
    def favorites_count(self, obj):
        return obj.favorites_count_annotation

    @admin.display(description="Изображение")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50"'
                + 'style="object-fit: cover;" />',
                obj.image.url,
            )
        return "-"


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "amount")
    search_fields = ("recipe__name", "ingredient__name")
    list_filter = ("ingredient",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipe',
                                                            'ingredient')


class UserRecipeAdminMixin:
    list_display = ("get_user", "get_recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'recipe')

    @admin.display(description="Пользователь")
    def get_user(self, obj):
        return obj.user.username

    @admin.display(description="Рецепт")
    def get_recipe(self, obj):
        return obj.recipe.name


@admin.register(Favorite)
class FavoriteAdmin(UserRecipeAdminMixin, admin.ModelAdmin):
    pass


@admin.register(ShoppingCart)
class ShoppingCartAdmin(UserRecipeAdminMixin, admin.ModelAdmin):
    pass
