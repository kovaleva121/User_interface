from django.urls import path
from access_control.apps import AccessControlConfig
from access_control.views import (
    ResourceListCreateView,
    ResourceDetailView,
    ActionListCreateView,
    ActionDetailView,
    RoleListCreateView,
    RoleDetailView,
    RolePermissionListCreateView,
    RolePermissionDeleteView,
    UserRoleListCreateView,
    UserRoleDeleteView,
    UserRolesView,
    MyPermissionsView,
)

app_name = AccessControlConfig.name

urlpatterns = [
    # Ресурсы
    path('resources/', ResourceListCreateView.as_view(), name='resource_list'),
    path('resources/<int:pk>/', ResourceDetailView.as_view(), name='resource_detail'),

    # Действия
    path('actions/', ActionListCreateView.as_view(), name='action_list'),
    path('actions/<int:pk>/', ActionDetailView.as_view(), name='action_detail'),

    # Роли
    path('roles/', RoleListCreateView.as_view(), name='role_list'),
    path('roles/<int:pk>/', RoleDetailView.as_view(), name='role_detail'),

    # Разрешения роли
    path('roles/<int:role_id>/permissions/', RolePermissionListCreateView.as_view(), name='role_permissions'),
    path('roles/<int:role_id>/permissions/<int:permission_id>/', RolePermissionDeleteView.as_view(),
         name='role_permission_delete'),

    # Назначение ролей пользователям
    path('user-roles/', UserRoleListCreateView.as_view(), name='user_role_list'),
    path('user-roles/<int:pk>/', UserRoleDeleteView.as_view(), name='user_role_delete'),
    path('users/<int:user_id>/roles/', UserRolesView.as_view(), name='user_roles'),

    # Собственные права текущего пользователя
    path('my-permissions/', MyPermissionsView.as_view(), name='my_permissions'),
]
