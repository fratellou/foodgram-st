from django.contrib import admin
from django.utils.html import format_html
from .models import Ingredient, Recipe, RecipeIngredient
from .models import Favorite, ShoppingCart


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

    @admin.display(description="В избранном")
    def favorites_count(self, obj):
        return obj.favorite_recipe.count()

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


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)
