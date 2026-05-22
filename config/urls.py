from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('access/', include('access_control.urls', namespace='access_control')),
    path('business/', include('business.urls', namespace='business')),
]
