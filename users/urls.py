# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    PhoneTokenObtainPairView,
    ProfileView,
    RegisterView,
    ToggleUserStatusView,
    UpdateUserRoleView,
    UserListView,
    save_fcm_token,
)

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('list/', UserListView.as_view(), name='user-list'),
    path('<int:user_id>/update-role/', UpdateUserRoleView.as_view(), name='update-role'),
    path('<int:user_id>/toggle-status/', ToggleUserStatusView.as_view(), name='toggle-status'),
    path('save-fcm-token/', save_fcm_token, name='save-fcm-token'),
    path('login/', PhoneTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
]