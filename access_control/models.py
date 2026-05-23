from django.db import models
from django.conf import settings


class Resource(models.Model):
    """
    Ресурс — объект системы, к которому ограничивается доступ.
    Примеры: 'orders', 'products', 'reports', 'users'
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Ресурс'
        verbose_name_plural = 'Ресурсы'

    def __str__(self):
        return self.name


class Action(models.Model):
    """
    Действие над ресурсом.
    Примеры: 'read', 'create', 'update', 'delete'
    """
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Действие'
        verbose_name_plural = 'Действия'

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    Роль — набор разрешений.
    Примеры: 'admin', 'manager', 'viewer'
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Связь: Роль → Действие → Ресурс.
    Определяет, что данная роль может выполнять конкретное действие над конкретным ресурсом.

    Пример: role=manager, action=read, resource=orders
    → менеджер может читать заказы.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Роль',
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Ресурс',
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Действие',
    )

    class Meta:
        verbose_name = 'Разрешение роли'
        verbose_name_plural = 'Разрешения ролей'
        unique_together = ('role', 'resource', 'action')  # одна запись на связку

    def __str__(self):
        return f'{self.role.name} | {self.action.name} | {self.resource.name}'


class UserRole(models.Model):
    """
    Назначение роли пользователю.
    Один пользователь может иметь несколько ролей.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='Пользователь',
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='Роль',
    )

    class Meta:
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'
        unique_together = ('user', 'role')

    def __str__(self):
        return f'{self.user.email} → {self.role.name}'
