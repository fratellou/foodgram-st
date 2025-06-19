from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    EMAIL_MAX_LENGTH = 254
    USERNAME_MAX_LENGTH = 150
    NAME_MAX_LENGTH = 150
    AVATAR_UPLOAD_TO = 'avatars/'
    AVATAR_MAX_LENGTH = 500

    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH, unique=True,
        verbose_name="Адрес электронной почты"
    )

    username = models.CharField(
        unique=True,
        max_length=USERNAME_MAX_LENGTH,
        verbose_name="Никнейм",
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message=(
                    "Никнейм пользователя может содержать только буквы,"
                    " цифры и символы: . @ + - _"
                ),
            )
        ],
    )

    first_name = models.CharField(max_length=NAME_MAX_LENGTH,
                                  verbose_name="Имя")

    last_name = models.CharField(max_length=NAME_MAX_LENGTH,
                                 verbose_name="Фамилия")

    avatar = models.ImageField(
        verbose_name="Изображение аватара",
        blank=True,
        default='',
        upload_to=AVATAR_UPLOAD_TO
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "last_name", "first_name"]

    class Meta:
        ordering = ["id"]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="Подписчик",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    author = models.ForeignKey(
        User,
        verbose_name="Подписан",
        on_delete=models.CASCADE,
        related_name="subscribers",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_subscribe")
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.user.username} подписан на {self.author.username}"
