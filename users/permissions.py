from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Разрешает доступ только пользователям с is_staff=True или is_superuser=True.
    При отказе: 403 Forbidden.
    """
    message = 'Доступ разрешён только администраторам.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Разрешает доступ к объекту только его владельцу или администратору.
    Используется в has_object_permission — вызывается после has_permission.
    При отказе: 403 Forbidden.
    """
    message = 'Вы можете управлять только своим профилем.'

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj == request.user
