from django.contrib.auth.models import AbstractUser
from django.db import models
from recipes.models import Recipe


class CustomUser(AbstractUser):
    email = models.EmailField(
        'Электронная почта',
        unique=True,
        blank=False,
        null=False)
    favorites = models.ManyToManyField(
        Recipe,
        related_name='favorited_by',
        blank=True,
        verbose_name='Избранные рецепты'
    )
    subscriptions = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='subscribers',
        blank=True,
        verbose_name='Подписки'
    )
    avatar = models.ImageField(
        upload_to='users/profile_pics/',
        null=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.lower()

        if self.pk:
            try:
                old = self.__class__.objects.get(pk=self.pk)
                if old.avatar and old.avatar != self.avatar:
                    old.avatar.delete(save=False)
            except self.__class__.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
