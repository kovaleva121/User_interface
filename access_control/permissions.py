from rest_framework.permissions import BasePermission
from access_control.models import RolePermission


def user_has_permission(user, resource_name: str, action_name: str) -> bool:
    """
    Вспомогательная функция.
    Проверяет, есть ли у пользователя разрешение выполнить action над resource
    через любую из его ролей.

    Логика:
      UserRole → Role → RolePermission → (Resource + Action)
    """
    if not user or not user.is_authenticated:
        return False

    # Суперпользователь имеет доступ ко всему
    if user.is_superuser:
        return True

    return RolePermission.objects.filter(
        role__user_roles__user=user,
        resource__name=resource_name,
        action__name=action_name,
    ).exists()


class RBACPermission(BasePermission):
    """
    Базовый класс для разграничения прав через RBAC.

    Использование во вьюхах:
        class OrderListView(APIView):
            permission_classes = [IsAuthenticated, RBACPermission]
            rbac_resource = 'orders'
            rbac_action = 'read'

    Если пользователь не аутентифицирован → 401.
    Если аутентифицирован, но нет прав → 403.
    """
    rbac_resource: str = None
    rbac_action: str = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        resource = getattr(view, 'rbac_resource', self.rbac_resource)
        action = getattr(view, 'rbac_action', self.rbac_action)

        if not resource or not action:
            return False

        has_access = user_has_permission(request.user, resource, action)

        if not has_access:
            self.message = (
                f'У вас нет права "{action}" на ресурс "{resource}".'
            )

        return has_access


class CanReadOrders(RBACPermission):
    rbac_resource = 'orders'
    rbac_action = 'read'


class CanCreateOrders(RBACPermission):
    rbac_resource = 'orders'
    rbac_action = 'create'


class CanUpdateOrders(RBACPermission):
    rbac_resource = 'orders'
    rbac_action = 'update'


class CanDeleteOrders(RBACPermission):
    rbac_resource = 'orders'
    rbac_action = 'delete'


class CanReadProducts(RBACPermission):
    rbac_resource = 'products'
    rbac_action = 'read'


class CanCreateProducts(RBACPermission):
    rbac_resource = 'products'
    rbac_action = 'create'


class CanUpdateProducts(RBACPermission):
    rbac_resource = 'products'
    rbac_action = 'update'


class CanDeleteProducts(RBACPermission):
    rbac_resource = 'products'
    rbac_action = 'delete'


class CanReadReports(RBACPermission):
    rbac_resource = 'reports'
    rbac_action = 'read'
