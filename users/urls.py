# users/urls.py
from django.urls import path
from .views import RegisterView, ProfileView
from .views import UserListView, UpdateUserRoleView, ToggleUserStatusView, save_fcm_token

try:
    from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
except ImportError:
    TokenObtainPairView = None
    TokenRefreshView = None

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('list/', UserListView.as_view(), name='user-list'),
    path('<int:user_id>/update-role/', UpdateUserRoleView.as_view(), name='update-role'),
    path('<int:user_id>/toggle-status/', ToggleUserStatusView.as_view(), name='toggle-status'),
    path('save-fcm-token/', save_fcm_token, name='save-fcm-token'),
]

if TokenObtainPairView is not None:
    urlpatterns += [
        path('login/', TokenObtainPairView.as_view(), name='login'),
        path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    ]