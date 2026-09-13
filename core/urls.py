# core/urls.py
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import SettingsView, PublicSettingsView, AnalyticsView

app_name = 'core'

urlpatterns = [
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/public/', PublicSettingsView.as_view(), name='public-settings'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'), # ✅ ДОБАВЛЕНО
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]