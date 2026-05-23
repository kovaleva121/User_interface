"""
Тесты моделей access_control (RBAC).
"""
from django.test import TestCase
from django.db import IntegrityError


class ResourceModelTest(TestCase):

    def test_create_resource(self):
        r = Resource.objects.create(name='orders', description='Заказы')
        self.assertEqual(r.name, 'orders')
        self.assertEqual(r.description, 'Заказы')


class ActionModelTest(TestCase):

    def test_create_action(self):
        a = Action.objects.create(name='read', description='Просмотр')
        self.assertEqual(a.name, 'read')


class RoleModelTest(TestCase):

    def test_create_role(self):
        role = Role.objects.create(name='admin', description='Администратор')
        self.assertEqual(role.name, 'admin')


class RolePermissionModelTest(TestCase):

    def setUp(self):
        self.role = Role.objects.create(name='tester')
        self.resource = Resource.objects.create(name='orders')
        self.action = Action.objects.create(name='read')

    def test_create_role_permission(self):
        rp = RolePermission.objects.create(
            role=self.role,
            resource=self.resource,
            action=self.action,
        )
        self.assertEqual(rp.role, self.role)
        self.assertEqual(rp.resource, self.resource)
        self.assertEqual(rp.action, self.action)

    def test_different_actions_allowed(self):
        """Для одной роли+ресурса можно создать разные действия."""
        action2 = Action.objects.create(name='create')
        RolePermission.objects.create(role=self.role, resource=self.resource, action=self.action)
        rp2 = RolePermission.objects.create(role=self.role, resource=self.resource, action=action2)
        self.assertIsNotNone(rp2.pk)

    def test_cascade_delete_role(self):
        """Удаление роли удаляет все её RolePermission."""
        RolePermission.objects.create(
            role=self.role, resource=self.resource, action=self.action
        )
        self.role.delete()
        self.assertEqual(RolePermission.objects.count(), 0)

    def test_cascade_delete_resource(self):
        """Удаление ресурса удаляет все его RolePermission."""
        RolePermission.objects.create(
            role=self.role, resource=self.resource, action=self.action
        )
        self.resource.delete()
        self.assertEqual(RolePermission.objects.count(), 0)

    def test_cascade_delete_action(self):
        """Удаление действия удаляет все его RolePermission."""
        RolePermission.objects.create(
            role=self.role, resource=self.resource, action=self.action
        )
        self.action.delete()
        self.assertEqual(RolePermission.objects.count(), 0)


class UserRoleModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='userrole@example.com', password='Pass1234!'
        )
        self.role = Role.objects.create(name='editor')

    def test_create_user_role(self):
        ur = UserRole.objects.create(user=self.user, role=self.role)
        self.assertEqual(ur.user, self.user)
        self.assertEqual(ur.role, self.role)

    def test_user_can_have_multiple_roles(self):
        """Один пользователь может иметь несколько ролей."""
        role2 = Role.objects.create(name='viewer_x')
        UserRole.objects.create(user=self.user, role=self.role)
        ur2 = UserRole.objects.create(user=self.user, role=role2)
        self.assertIsNotNone(ur2.pk)
        self.assertEqual(UserRole.objects.filter(user=self.user).count(), 2)

    def test_cascade_delete_user(self):
        """Удаление пользователя удаляет его UserRole."""
        UserRole.objects.create(user=self.user, role=self.role)
        self.user.delete()
        self.assertEqual(UserRole.objects.count(), 0)

    def test_cascade_delete_role(self):
        """Удаление роли удаляет все UserRole с ней."""
        UserRole.objects.create(user=self.user, role=self.role)
        self.role.delete()
        self.assertEqual(UserRole.objects.count(), 0)


"""
Тесты вьюх access_control (управление правами).
"""
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from access_control.models import Action, Resource, Role, RolePermission, UserRole


def get_access_token(user: User) -> str:
    return str(RefreshToken.for_user(user).access_token)


def make_user(email, is_staff=False, is_superuser=False) -> User:
    u = User(email=email, is_staff=is_staff, is_superuser=is_superuser)
    u.set_password('Pass1234!')
    u.save()
    return u


class AdminOnlyMixin:
    """
    Миксин для проверки, что эндпоинт требует прав администратора.
    Переопределяется в каждом тест-классе: задаёт url и метод.
    """
    url: str = None
    method: str = 'get'
    payload: dict = {}

    def setUp(self):
        self.admin = make_user('admin@example.com', is_staff=True, is_superuser=True)
        self.user = make_user('user@example.com')

    def _call(self, client_user=None, use_auth=True):
        if use_auth and client_user:
            self.client.credentials(
                HTTP_AUTHORIZATION=f'Bearer {get_access_token(client_user)}'
            )
        elif not use_auth:
            self.client.credentials()
        return getattr(self.client, self.method)(self.url, self.payload, format='json')

    def test_unauthenticated_gets_401(self):
        resp = self._call(use_auth=False)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_gets_403(self):
        resp = self._call(client_user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ResourceListCreateTest(AdminOnlyMixin, APITestCase):
    url = '/access/resources/'
    method = 'get'

    def test_admin_can_list_resources(self):
        Resource.objects.create(name='orders')
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_admin_can_create_resource(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(
            self.url, {'name': 'products', 'description': 'Товары'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Resource.objects.filter(name='products').exists())

    def test_create_duplicate_resource_400(self):
        Resource.objects.create(name='orders')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(self.url, {'name': 'orders'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ResourceDetailTest(AdminOnlyMixin, APITestCase):
    method = 'get'

    def setUp(self):
        super().setUp()
        self.resource = Resource.objects.create(name='orders', description='Заказы')
        self.url = f'/access/resources/{self.resource.pk}/'

    def test_admin_can_retrieve_resource(self):
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'orders')

    def test_admin_can_update_resource(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.patch(self.url, {'description': 'Обновлено'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.description, 'Обновлено')

    def test_admin_can_delete_resource(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resource.objects.filter(pk=self.resource.pk).exists())

    def test_nonexistent_resource_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get('/access/resources/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ActionListCreateTest(AdminOnlyMixin, APITestCase):
    url = '/access/actions/'
    method = 'get'

    def test_admin_can_create_action(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(self.url, {'name': 'read', 'description': 'Просмотр'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_can_list_actions(self):
        Action.objects.create(name='read')
        Action.objects.create(name='create')
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)


class RoleListCreateTest(AdminOnlyMixin, APITestCase):
    url = '/access/roles/'
    method = 'get'

    def test_admin_can_list_roles(self):
        Role.objects.create(name='admin')
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_create_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(self.url, {'name': 'editor', 'description': 'Редактор'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Role.objects.filter(name='editor').exists())

    def test_role_list_includes_permissions(self):
        """В список ролей включаются вложенные разрешения."""
        role = Role.objects.create(name='manager')
        resource = Resource.objects.create(name='orders')
        action = Action.objects.create(name='read')
        RolePermission.objects.create(role=role, resource=resource, action=action)

        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        role_data = next(r for r in resp.data if r['name'] == 'manager')
        self.assertEqual(len(role_data['permissions']), 1)


class RoleDetailTest(AdminOnlyMixin, APITestCase):
    method = 'get'

    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name='viewer')
        self.url = f'/access/roles/{self.role.pk}/'

    def test_admin_can_retrieve_role(self):
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'viewer')

    def test_admin_can_update_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.patch(self.url, {'description': 'Обновлено'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_delete_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Role.objects.filter(pk=self.role.pk).exists())


class RolePermissionViewTest(AdminOnlyMixin, APITestCase):
    method = 'get'

    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name='manager')
        self.resource = Resource.objects.create(name='orders')
        self.action = Action.objects.create(name='read')
        self.url = f'/access/roles/{self.role.pk}/permissions/'

    def test_admin_can_list_role_permissions(self):
        RolePermission.objects.create(role=self.role, resource=self.resource, action=self.action)
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['permissions']), 1)

    def test_admin_can_add_permission_to_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(
            self.url,
            {'resource_id': self.resource.pk, 'action_id': self.action.pk},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            RolePermission.objects.filter(
                role=self.role, resource=self.resource, action=self.action
            ).exists()
        )

    def test_duplicate_permission_400(self):
        RolePermission.objects.create(role=self.role, resource=self.resource, action=self.action)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(
            self.url,
            {'resource_id': self.resource.pk, 'action_id': self.action.pk},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permissions_for_nonexistent_role_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get('/access/roles/99999/permissions/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_permission(self):
        rp = RolePermission.objects.create(
            role=self.role, resource=self.resource, action=self.action
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(f'/access/roles/{self.role.pk}/permissions/{rp.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RolePermission.objects.filter(pk=rp.pk).exists())

    def test_delete_nonexistent_permission_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(f'/access/roles/{self.role.pk}/permissions/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class UserRoleViewTest(AdminOnlyMixin, APITestCase):
    url = '/access/user-roles/'
    method = 'get'

    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name='editor')

    def test_admin_can_assign_role_to_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(
            self.url,
            {'user_id': self.user.pk, 'role_id': self.role.pk},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            UserRole.objects.filter(user=self.user, role=self.role).exists()
        )

    def test_assign_duplicate_role_400(self):
        UserRole.objects.create(user=self.user, role=self.role)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(
            self.url,
            {'user_id': self.user.pk, 'role_id': self.role.pk},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_list_user_roles(self):
        UserRole.objects.create(user=self.user, role=self.role)
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_admin_can_revoke_role(self):
        ur = UserRole.objects.create(user=self.user, role=self.role)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(f'/access/user-roles/{ur.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserRole.objects.filter(pk=ur.pk).exists())

    def test_revoke_nonexistent_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete('/access/user-roles/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class UserRolesViewTest(AdminOnlyMixin, APITestCase):
    method = 'get'

    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name='viewer')
        UserRole.objects.create(user=self.user, role=self.role)
        self.url = f'/access/users/{self.user.pk}/roles/'

    def test_admin_sees_user_roles(self):
        resp = self._call(client_user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['roles']), 1)
        self.assertEqual(resp.data['roles'][0]['name'], 'viewer')

    def test_nonexistent_user_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get('/access/users/99999/roles/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class MyPermissionsViewTest(APITestCase):
    url = '/access/my-permissions/'

    def setUp(self):
        self.user = make_user('me@example.com')
        self.role = Role.objects.create(name='analyst')
        self.resource = Resource.objects.create(name='reports')
        self.action = Action.objects.create(name='read')
        RolePermission.objects.create(role=self.role, resource=self.resource, action=self.action)
        UserRole.objects.create(user=self.user, role=self.role)

    def test_authenticated_user_sees_own_permissions(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.user)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['user'], 'me@example.com')
        self.assertIn('analyst', resp.data['roles'])
        self.assertEqual(len(resp.data['permissions']), 1)
        self.assertEqual(resp.data['permissions'][0]['resource'], 'reports')
        self.assertEqual(resp.data['permissions'][0]['action'], 'read')

    def test_unauthenticated_gets_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_roles_sees_empty_permissions(self):
        new_user = make_user('noroles@example.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(new_user)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['roles'], [])
        self.assertEqual(resp.data['permissions'], [])
