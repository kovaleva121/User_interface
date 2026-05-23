from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveAPIView,
    DestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from users.models import User
from users.serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    UserAdminSerializer,
)
from users.permissions import IsOwnerOrAdmin, IsAdminUser


class UserCreateApiView(CreateAPIView):
    """
    POST /users/register/
    Регистрация нового пользователя. Доступно без аутентификации.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class UserListApiView(ListAPIView):
    """
    GET /users/list/
    Список всех пользователей. Только для администратора.
    """
    serializer_class = UserAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return User.objects.all().order_by('id')


class UserRetrieveApiView(RetrieveAPIView):
    """
    GET /users/<pk>/detail/
    Просмотр профиля.
    - Обычный пользователь: только свой профиль.
    - Администратор: любой профиль.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_serializer_class(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return UserAdminSerializer
        return UserProfileSerializer

    def get_queryset(self):
        return User.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj


class UserUpdateApiView(UpdateAPIView):
    """
    PUT/PATCH /users/<pk>/update/
    Обновление профиля. Только владелец или администратор.
    Если передан пароль — хешируется через set_password.
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return User.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class UserDestroyApiView(DestroyAPIView):
    """
    DELETE /users/<pk>/delete/
    Мягкое удаление: is_active=False + инвалидация JWT-токенов.
    Только владелец или администратор.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return User.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        instance.soft_delete()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'detail': 'Аккаунт деактивирован. Вы будете разлогинены.'},
            status=status.HTTP_200_OK,
        )


class LogoutApiView(APIView):
    """
    POST /users/logout/
    Инвалидация refresh-токена — помещает его в blacklist.
    После этого токен нельзя использовать для получения нового access.

    Тело запроса: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'detail': 'Необходимо передать refresh-токен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Токен недействителен или уже использован.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {'detail': 'Вы успешно вышли из системы.'},
            status=status.HTTP_205_RESET_CONTENT,
        )
