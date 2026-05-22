from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.apps import UsersConfig
from users.views import (
    UserCreateApiView,
    UserListApiView,
    UserRetrieveApiView,
    UserUpdateApiView,
    UserDestroyApiView,
    LogoutApiView,
)

app_name = UsersConfig.name

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(permission_classes=(AllowAny,)), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(permission_classes=(AllowAny,)), name='token_refresh'),
    path('logout/', LogoutApiView.as_view(), name='logout'),
    path('register/', UserCreateApiView.as_view(), name='user_create'),
    path('list/', UserListApiView.as_view(), name='user_list'),
    path('<int:pk>/detail/', UserRetrieveApiView.as_view(), name='user_retrieve'),
    path('<int:pk>/update/', UserUpdateApiView.as_view(), name='user_update'),
    path('<int:pk>/delete/', UserDestroyApiView.as_view(), name='user_delete'),
]
