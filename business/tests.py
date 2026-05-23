"""
Тесты Mock-вьюх бизнес-объектов (orders, products, reports).

Для каждого ресурса проверяем:
  - 401 без токена
  - 403 для пользователя без нужной роли
  - 200/201/204 для пользователя с нужной ролью
  - Матрицу ролей: viewer видит orders/products, но не reports и не может изменять
  - manager не может удалять
  - admin может всё
"""
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from access_control.models import Action, Resource, Role, RolePermission, UserRole


def get_access_token(user: User) -> str:
    return str(RefreshToken.for_user(user).access_token)


def make_user(email, is_superuser=False) -> User:
    u = User(email=email, is_superuser=is_superuser, is_staff=is_superuser)
    u.set_password('Pass1234!')
    u.save()
    return u


def grant(user: User, resource_name: str, action_name: str):
    """Назначает пользователю право resource:action через уникальную роль."""
    role_name = f'role_{resource_name}_{action_name}'
    role, _ = Role.objects.get_or_create(name=role_name)
    resource, _ = Resource.objects.get_or_create(name=resource_name)
    action, _ = Action.objects.get_or_create(name=action_name)
    RolePermission.objects.get_or_create(role=role, resource=resource, action=action)
    UserRole.objects.get_or_create(user=user, role=role)


def setup_role_matrix():
    """
    Создаёт трёх пользователей с полной матрицей прав, как в seed_data:
      admin_user  → всё на всём (через is_superuser)
      manager     → read/create/update на orders+products; read на reports
      viewer      → только read на orders+products
    """
    admin_user = make_user('admin@biz.example.com', is_superuser=True)

    manager = make_user('manager@biz.example.com')
    for res in ('orders', 'products'):
        for act in ('read', 'create', 'update'):
            grant(manager, res, act)
    grant(manager, 'reports', 'read')

    viewer = make_user('viewer@biz.example.com')
    grant(viewer, 'orders', 'read')
    grant(viewer, 'products', 'read')

    no_role = make_user('norole@biz.example.com')

    return admin_user, manager, viewer, no_role


class OrderListViewTest(APITestCase):
    """GET /business/orders/  — требует orders:read"""

    url = '/business/orders/'

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def test_unauthenticated_gets_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_user_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.no_role)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_can_read_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_can_read_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_read_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_response_contains_data_and_count(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertIn('data', resp.data)
        self.assertIn('count', resp.data)
        self.assertIsInstance(resp.data['data'], list)
        self.assertGreater(resp.data['count'], 0)

    def test_response_resource_field_is_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['resource'], 'orders')


class OrderCreateViewTest(APITestCase):
    """POST /business/orders/create/  — требует orders:create"""

    url = '/business/orders/create/'

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def test_unauthenticated_gets_401(self):
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_create_orders_403(self):
        """viewer имеет только read — создавать нельзя."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.post(self.url, {'client': 'Тест'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.post(self.url, {'client': 'ООО Тест', 'product': 'Товар'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_can_create_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(self.url, {'client': 'Admin Corp'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_created_order_has_pending_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.post(self.url, {'client': 'Тест'}, format='json')
        self.assertEqual(resp.data['data']['status'], 'pending')


class OrderUpdateViewTest(APITestCase):
    """PUT /business/orders/<pk>/update/  — требует orders:update"""

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def _url(self, pk=1):
        return f'/business/orders/{pk}/update/'

    def test_unauthenticated_gets_401(self):
        resp = self.client.put(self._url(), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_update_orders_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.put(self._url(), {'status': 'shipped'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_update_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.put(self._url(1), {'status': 'shipped'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_update_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.put(self._url(1), {'status': 'delivered'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_update_nonexistent_order_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.put(self._url(9999), {'status': 'x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_updated_order_keeps_correct_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.put(self._url(2), {'status': 'cancelled'}, format='json')
        self.assertEqual(resp.data['data']['id'], 2)


class OrderDeleteViewTest(APITestCase):
    """DELETE /business/orders/<pk>/delete/  — требует orders:delete"""

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def _url(self, pk=1):
        return f'/business/orders/{pk}/delete/'

    def test_unauthenticated_gets_401(self):
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_delete_orders_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_delete_orders_403(self):
        """manager имеет только read/create/update — удалять нельзя."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self._url(1))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_nonexistent_order_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self._url(9999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ProductListViewTest(APITestCase):
    """GET /business/products/  — требует products:read"""

    url = '/business/products/'

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def test_unauthenticated_gets_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_role_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.no_role)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_can_read_products(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_can_read_products(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_read_products(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['resource'], 'products')
        self.assertIn('data', resp.data)
        self.assertGreater(len(resp.data['data']), 0)


class ProductCreateViewTest(APITestCase):
    """POST /business/products/create/  — требует products:create"""

    url = '/business/products/create/'

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def test_unauthenticated_gets_401(self):
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_create_products_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.post(self.url, {'name': 'Тестовый товар'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.post(self.url, {'name': 'Новый товар', 'price': 1000}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_can_create_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.post(self.url, {'name': 'Admin Товар'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class ProductUpdateViewTest(APITestCase):
    """PUT /business/products/<pk>/update/  — требует products:update"""

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def _url(self, pk=1):
        return f'/business/products/{pk}/update/'

    def test_unauthenticated_gets_401(self):
        resp = self.client.put(self._url(), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_update_products_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.put(self._url(), {'price': 9999}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_update_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.put(self._url(1), {'price': 99000}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_update_nonexistent_product_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.put(self._url(9999), {'price': 0}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_updated_product_has_correct_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.put(self._url(3), {'price': 5000}, format='json')
        self.assertEqual(resp.data['data']['id'], 3)


class ProductDeleteViewTest(APITestCase):
    """DELETE /business/products/<pk>/delete/  — требует products:delete"""

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def _url(self, pk=1):
        return f'/business/products/{pk}/delete/'

    def test_unauthenticated_gets_401(self):
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_delete_products_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_delete_products_403(self):
        """У менеджера нет products:delete."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.delete(self._url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self._url(2))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_nonexistent_product_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.delete(self._url(9999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ReportListViewTest(APITestCase):
    """GET /business/reports/  — требует reports:read"""

    url = '/business/reports/'

    def setUp(self):
        self.admin, self.manager, self.viewer, self.no_role = setup_role_matrix()

    def test_unauthenticated_gets_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_cannot_read_reports_403(self):
        """viewer не имеет rights на reports — ключевая проверка матрицы."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.viewer)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_role_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.no_role)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_read_reports(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_read_reports(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.admin)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_access_token(self.manager)}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['resource'], 'reports')
        self.assertIn('data', resp.data)
        self.assertGreater(len(resp.data['data']), 0)
