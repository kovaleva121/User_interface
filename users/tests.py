"""
Тесты модели users.User.

Покрываем:
  - создание пользователя и хеширование пароля
  - уникальность email
  - __str__ и get_full_name
  - soft_delete: запись остаётся в БД, is_active=False
  - невозможность входа после soft_delete
  - поведение флагов is_staff / is_superuser
"""
from django.test import TestCase
from django.db import IntegrityError

from users.models import User


class UserModelCreationTest(TestCase):
    """Тесты создания и базовых полей пользователя."""

    def test_create_user_basic(self):
        """Пользователь создаётся с корректными полями."""
        user = User.objects.create_user(
            email='test@example.com',
            password='Pass1234!',
            first_name='Анна',
            last_name='Петрова',
            patronymic='Сергеевна',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Анна')
        self.assertEqual(user.last_name, 'Петрова')
        self.assertEqual(user.patronymic, 'Сергеевна')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed(self):
        """Пароль хранится в хешированном виде, не в открытом."""
        user = User.objects.create_user(email='hash@example.com', password='PlainPass1!')
        self.assertNotEqual(user.password, 'PlainPass1!')
        self.assertTrue(user.password.startswith('pbkdf2_sha256'))

    def test_check_password(self):
        """check_password возвращает True для правильного пароля."""
        user = User.objects.create_user(email='check@example.com', password='MySecret99!')
        self.assertTrue(user.check_password('MySecret99!'))
        self.assertFalse(user.check_password('WrongPass'))

    def test_email_is_unique(self):
        """Нельзя создать двух пользователей с одинаковым email."""
        User.objects.create_user(email='dup@example.com', password='Pass1234!')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='dup@example.com', password='AnotherPass1!')

    def test_username_field_is_email(self):
        """USERNAME_FIELD должен быть email."""
        self.assertEqual(User.USERNAME_FIELD, 'email')

    def test_required_fields_empty(self):
        """REQUIRED_FIELDS пуст — email достаточен для создания."""
        self.assertEqual(User.REQUIRED_FIELDS, [])


class UserSoftDeleteTest(TestCase):
    """Тесты мягкого удаления пользователя."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='delete@example.com',
            password='Pass1234!',
        )

    def test_soft_delete_sets_is_active_false(self):
        """soft_delete устанавливает is_active=False."""
        self.user.soft_delete()
        self.assertFalse(self.user.is_active)

    def test_soft_delete_keeps_record_in_db(self):
        """После soft_delete запись остаётся в БД."""
        self.user.soft_delete()
        exists = User.objects.filter(email='delete@example.com').exists()
        self.assertTrue(exists)

    def test_soft_deleted_user_is_persisted(self):
        """После soft_delete is_active=False сохранён в БД."""
        self.user.soft_delete()
        refreshed = User.objects.get(pk=self.user.pk)
        self.assertFalse(refreshed.is_active)

    def test_soft_delete_does_not_change_email(self):
        """soft_delete не трогает другие поля."""
        self.user.soft_delete()
        refreshed = User.objects.get(pk=self.user.pk)
        self.assertEqual(refreshed.email, 'delete@example.com')

    def test_active_user_count_decreases_after_soft_delete(self):
        """После soft_delete активных пользователей становится меньше."""
        active_before = User.objects.filter(is_active=True).count()
        self.user.soft_delete()
        active_after = User.objects.filter(is_active=True).count()
        self.assertEqual(active_after, active_before - 1)


class UserFlagsTest(TestCase):
    """Тесты флагов is_staff и is_superuser."""

    def test_default_user_not_staff(self):
        user = User.objects.create_user(email='nostaff@example.com', password='Pass1234!')
        self.assertFalse(user.is_staff)

    def test_superuser_is_staff_and_superuser(self):
        admin = User.objects.create_superuser(email='super@example.com', password='Pass1234!')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_inactive_user_cannot_authenticate(self):
        """Деактивированный пользователь не может аутентифицироваться."""
        from django.contrib.auth import authenticate
        user = User.objects.create_user(email='inactive@example.com', password='Pass1234!')
        user.soft_delete()
        result = authenticate(email='inactive@example.com', password='Pass1234!')
        self.assertIsNone(result)


"""
Тесты вьюх пакета users.
"""

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


def get_tokens(user: User) -> dict:
    """Возвращает {'access': ..., 'refresh': ...} для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def auth_header(user: User) -> dict:
    """Возвращает заголовок Authorization для передачи в APIClient."""
    tokens = get_tokens(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


class UserRegisterViewTest(APITestCase):
    """POST /users/register/"""

    url = '/users/register/'

    def _payload(self, **kwargs):
        base = {
            'email': 'new@example.com',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'patronymic': 'Иванович',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        base.update(kwargs)
        return base

    def test_register_success_201(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

    def test_register_returns_email_not_password(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertIn('email', response.data)
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_confirm', response.data)

    def test_register_no_auth_required(self):
        """Регистрация доступна без токена."""
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registered_user_is_active(self):
        self.client.post(self.url, self._payload(), format='json')
        user = User.objects.get(email='new@example.com')
        self.assertTrue(user.is_active)


class UserLoginViewTest(APITestCase):
    """POST /users/login/"""

    url = '/users/login/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='login@example.com', password='Pass1234!'
        )

    def test_login_success_returns_tokens(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'Pass1234!'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password_401(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'WrongPass!'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user_401(self):
        """Деактивированный пользователь не может войти."""
        self.user.soft_delete()
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'Pass1234!'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserTokenRefreshViewTest(APITestCase):
    """POST /users/token/refresh/"""

    url = '/users/token/refresh/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='refresh@example.com', password='Pass1234!'
        )
        self.tokens = get_tokens(self.user)

    def test_refresh_returns_new_access(self):
        response = self.client.post(
            self.url, {'refresh': self.tokens['refresh']}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_with_invalid_token_401(self):
        response = self.client.post(self.url, {'refresh': 'invalid.token.here'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserLogoutViewTest(APITestCase):
    """POST /users/logout/"""

    url = '/users/logout/'

    def setUp(self):
        self.user = User.objects.create_user(
            email='logout@example.com', password='Pass1234!'
        )
        self.tokens = get_tokens(self.user)

    def test_logout_success_205(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["access"]}')
        response = self.client.post(self.url, {'refresh': self.tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_blacklists_refresh_token(self):
        """После logout refresh-токен нельзя использовать снова."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["access"]}')
        self.client.post(self.url, {'refresh': self.tokens['refresh']}, format='json')

        # Пытаемся использовать тот же refresh
        response = self.client.post('/users/token/refresh/', {'refresh': self.tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_auth_401(self):
        """Без токена logout недоступен."""
        response = self.client.post(self.url, {'refresh': self.tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_body_400(self):
        """Logout без refresh в теле → 400."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["access"]}')
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_with_invalid_refresh_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["access"]}')
        response = self.client.post(self.url, {'refresh': 'bad.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserListViewTest(APITestCase):
    """GET /users/list/"""

    url = '/users/list/'

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com', password='Pass1234!', is_staff=True, is_superuser=True
        )
        self.user = User.objects.create_user(
            email='user@example.com', password='Pass1234!'
        )

    def test_admin_can_list_users(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.admin)["access"]}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_regular_user_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserRetrieveViewTest(APITestCase):
    """GET /users/<pk>/detail/"""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com', password='Pass1234!', is_staff=True, is_superuser=True
        )
        self.user = User.objects.create_user(
            email='user@example.com', password='Pass1234!'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com', password='Pass1234!'
        )

    def _url(self, pk):
        return f'/users/{pk}/detail/'

    def test_user_can_view_own_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.get(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user@example.com')

    def test_user_cannot_view_other_profile_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.get(self._url(self.other_user.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_any_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.admin)["access"]}')
        response = self.client.get(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_gets_401(self):
        response = self.client.get(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_response_includes_is_staff_field(self):
        """Администратор видит расширенные поля."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.admin)["access"]}')
        response = self.client.get(self._url(self.user.pk))
        self.assertIn('is_staff', response.data)


class UserUpdateViewTest(APITestCase):
    """PATCH /users/<pk>/update/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='upd@example.com', password='Pass1234!', first_name='Старое'
        )
        self.other = User.objects.create_user(
            email='other@example.com', password='Pass1234!'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com', password='Pass1234!', is_staff=True, is_superuser=True
        )

    def _url(self, pk):
        return f'/users/{pk}/update/'

    def test_user_can_update_own_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.patch(self._url(self.user.pk), {'first_name': 'Новое'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Новое')

    def test_user_cannot_update_other_profile_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.patch(self._url(self.other.pk), {'first_name': 'Хак'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.admin)["access"]}')
        response = self.client.patch(self._url(self.user.pk), {'first_name': 'ОтАдмина'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_gets_401(self):
        response = self.client.patch(self._url(self.user.pk), {'first_name': 'X'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDestroyViewTest(APITestCase):
    """DELETE /users/<pk>/delete/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='del@example.com', password='Pass1234!'
        )
        self.other = User.objects.create_user(
            email='other@example.com', password='Pass1234!'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com', password='Pass1234!', is_staff=True, is_superuser=True
        )

    def _url(self, pk):
        return f'/users/{pk}/delete/'

    def test_user_can_soft_delete_own_account(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.delete(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_soft_delete_sets_is_active_false(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        self.client.delete(self._url(self.user.pk))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_soft_delete_keeps_record_in_db(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        self.client.delete(self._url(self.user.pk))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_user_cannot_delete_other_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        response = self.client.delete(self._url(self.other.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_any_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.admin)["access"]}')
        response = self.client.delete(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_gets_401(self):
        response = self.client.delete(self._url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deleted_user_cannot_login(self):
        """После мягкого удаления пользователь не может войти."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {get_tokens(self.user)["access"]}')
        self.client.delete(self._url(self.user.pk))
        self.client.credentials()  # сбросить токен
        response = self.client.post(
            '/users/login/',
            {'email': 'del@example.com', 'password': 'Pass1234!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
