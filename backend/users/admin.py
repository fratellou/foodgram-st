from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Subscribe
from recipes.models import Recipe


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'full_name', 'display_avatar',
                    'recipes_count', 'subscribers_count',
                    'subscriptions_count')

    search_fields = ('username', 'email')

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Персональные данные', {
            'fields': ('first_name',
                       'last_name',
                       'avatar')
        })
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    empty_value_display = '-'

    @admin.display(description='ФИО')
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description='Рецепты')
    def recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    @admin.display(description='Аватар')
    def display_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url
            )
        return self.empty_value_display

    @admin.display(description='Подписчики')
    def subscribers_count(self, obj):
        return obj.subscribers.count()

    @admin.display(description='Подписки')
    def subscriptions_count(self, obj):
        return obj.subscriptions.count()


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')
    empty_value_display = '-'
