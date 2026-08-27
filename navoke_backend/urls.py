# navoke_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/products/', include('products.urls')),
    path('api/v1/orders/', include('orders.urls')),
    path('api/v1/payments/', include('payments.urls')),
]

# ✅ ДОБАВЛЕНО: ОТДАЧА МЕДИА-ФАЙЛОВ (изображений) В РЕЖИМЕ DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


urlpatterns += [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('catalog/', TemplateView.as_view(template_name='catalog.html'), name='catalog'),
    path('cart/', TemplateView.as_view(template_name='cart.html'), name='cart'),
    path('checkout/', TemplateView.as_view(template_name='checkout.html'), name='checkout'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('product/<int:product_id>/', TemplateView.as_view(template_name='product.html'), name='product'),
    path('admin-panel/', TemplateView.as_view(template_name='admin-panel.html'), name='admin-panel'),
    path('order-success/', TemplateView.as_view(template_name='order-success.html'), name='order-success'),
    path('api/v1/core/', include('core.urls')),
    path('order/<int:order_id>/', TemplateView.as_view(template_name='order-detail.html'), name='order-detail'),
    # ✅ ДОБАВЬТЕ ЭТО:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # В production используем WhiteNoise для медиа
    from django.views.static import serve
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
