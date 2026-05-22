from rest_framework import serializers
from access_control.models import Role, Resource, Action, RolePermission, UserRole
from users.models import User


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'name', 'description']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'name', 'description']


class RolePermissionSerializer(serializers.ModelSerializer):
    """Разрешение роли с вложенными данными ресурса и действия."""
    resource = ResourceSerializer(read_only=True)
    action = ActionSerializer(read_only=True)
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(), source='resource', write_only=True
    )
    action_id = serializers.PrimaryKeyRelatedField(
        queryset=Action.objects.all(), source='action', write_only=True
    )

    class Meta:
        model = RolePermission
        fields = ['id', 'resource', 'action', 'resource_id', 'action_id']

    def validate(self, attrs):
        role = self.context.get('role')
        resource = attrs.get('resource')
        action = attrs.get('action')
        if role and RolePermission.objects.filter(role=role, resource=resource, action=action).exists():
            raise serializers.ValidationError(
                'Такое разрешение для этой роли уже существует.'
            )
        return attrs


class RoleSerializer(serializers.ModelSerializer):
    """Роль со списком всех разрешений."""
    permissions = RolePermissionSerializer(
        source='role_permissions', many=True, read_only=True
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions']


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """Создание/обновление роли (без вложенных permissions)."""

    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


class UserRoleSerializer(serializers.ModelSerializer):
    """Назначение роли пользователю."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True
    )

    class Meta:
        model = UserRole
        fields = ['id', 'user_email', 'role_name', 'user_id', 'role_id']

    def validate(self, attrs):
        user = attrs.get('user')
        role = attrs.get('role')
        if UserRole.objects.filter(user=user, role=role).exists():
            raise serializers.ValidationError(
                f'Пользователь уже имеет роль "{role.name}".'
            )
        return attrs


class UserRolesListSerializer(serializers.ModelSerializer):
    """Список ролей конкретного пользователя."""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'roles']

    def get_roles(self, obj):
        user_roles = UserRole.objects.filter(user=obj).select_related('role')
        return [{'id': ur.role.id, 'name': ur.role.name} for ur in user_roles]
