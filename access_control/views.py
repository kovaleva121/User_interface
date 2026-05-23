from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from access_control.models import Role, Resource, Action, RolePermission, UserRole
from access_control.serializers import (
    RoleSerializer,
    RoleCreateUpdateSerializer,
    ResourceSerializer,
    ActionSerializer,
    RolePermissionSerializer,
    UserRoleSerializer,
    UserRolesListSerializer,
)
from users.models import User
from users.permissions import IsAdminUser


class ResourceListCreateView(ListCreateAPIView):
    """
    GET  /access/resources/      — список всех ресурсов
    POST /access/resources/      — создать ресурс (только admin)
    """
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class ResourceDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    /access/resources/<id>/  — детали ресурса
    PUT    /access/resources/<id>/  — обновить
    DELETE /access/resources/<id>/  — удалить
    Только admin.
    """
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class ActionListCreateView(ListCreateAPIView):
    """
    GET  /access/actions/   — список всех действий
    POST /access/actions/   — создать действие (только admin)
    """
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class ActionDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /access/actions/<id>/
    Только admin.
    """
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class RoleListCreateView(ListCreateAPIView):
    """
    GET  /access/roles/    — список всех ролей с их разрешениями
    POST /access/roles/    — создать роль (только admin)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return Role.objects.prefetch_related(
            'role_permissions__resource',
            'role_permissions__action',
        ).all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoleCreateUpdateSerializer
        return RoleSerializer


class RoleDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    /access/roles/<id>/  — детали роли
    PUT    /access/roles/<id>/  — обновить название/описание роли
    DELETE /access/roles/<id>/  — удалить роль
    Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return Role.objects.prefetch_related(
            'role_permissions__resource',
            'role_permissions__action',
        ).all()

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return RoleCreateUpdateSerializer
        return RoleSerializer


class RolePermissionListCreateView(APIView):
    """
    GET  /access/roles/<role_id>/permissions/  — все разрешения роли
    POST /access/roles/<role_id>/permissions/  — добавить разрешение роли
    Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_role(self, role_id):
        try:
            return Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return None

    def get(self, request, role_id):
        role = self.get_role(role_id)
        if not role:
            return Response({'detail': 'Роль не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        permissions = RolePermission.objects.filter(role=role).select_related('resource', 'action')
        serializer = RolePermissionSerializer(permissions, many=True)
        return Response({'role': role.name, 'permissions': serializer.data})

    def post(self, request, role_id):
        role = self.get_role(role_id)
        if not role:
            return Response({'detail': 'Роль не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RolePermissionSerializer(data=request.data, context={'role': role})
        if serializer.is_valid():
            serializer.save(role=role)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RolePermissionDeleteView(APIView):
    """
    DELETE /access/roles/<role_id>/permissions/<permission_id>/
    Удалить конкретное разрешение у роли. Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, role_id, permission_id):
        try:
            perm = RolePermission.objects.get(pk=permission_id, role_id=role_id)
        except RolePermission.DoesNotExist:
            return Response(
                {'detail': 'Разрешение не найдено.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        perm.delete()
        return Response(
            {'detail': 'Разрешение удалено.'},
            status=status.HTTP_204_NO_CONTENT,
        )


class UserRoleListCreateView(APIView):
    """
    GET  /access/user-roles/         — список всех назначений (user → role)
    POST /access/user-roles/         — назначить роль пользователю
    Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        user_roles = UserRole.objects.select_related('user', 'role').all()
        serializer = UserRoleSerializer(user_roles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserRoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRoleDeleteView(APIView):
    """
    DELETE /access/user-roles/<id>/
    Отозвать роль у пользователя. Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        try:
            user_role = UserRole.objects.get(pk=pk)
        except UserRole.DoesNotExist:
            return Response(
                {'detail': 'Запись не найдена.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        user_role.delete()
        return Response(
            {'detail': 'Роль у пользователя отозвана.'},
            status=status.HTTP_204_NO_CONTENT,
        )


class UserRolesView(APIView):
    """
    GET /access/users/<user_id>/roles/
    Показать все роли конкретного пользователя. Только admin.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserRolesListSerializer(user)
        return Response(serializer.data)


class MyPermissionsView(APIView):
    """
    GET /access/my-permissions/
    Показывает все права текущего аутентифицированного пользователя.
    Доступно любому авторизованному пользователю о себе.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        user_roles = UserRole.objects.filter(user=user).select_related('role')
        roles = [ur.role for ur in user_roles]

        permissions = RolePermission.objects.filter(
            role__in=roles
        ).select_related('role', 'resource', 'action')

        result = {
            'user': user.email,
            'roles': [r.name for r in roles],
            'permissions': [
                {
                    'resource': p.resource.name,
                    'action': p.action.name,
                }
                for p in permissions
            ],
        }
        return Response(result)
