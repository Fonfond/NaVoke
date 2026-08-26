# core/urls.py
from django.urls import path
from .views import SettingsView, PublicSettingsView, AnalyticsView

app_name = 'core'

urlpatterns = [
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/public/', PublicSettingsView.as_view(), name='public-settings'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'), # ✅ ДОБАВЛЕНО
]