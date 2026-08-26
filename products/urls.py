# products/urls.py
from django.urls import path
from .views import (
    ProductListView, ProductDetailView, CategoryListView,
    ToggleFavoriteView, FavoritesListView, CheckFavoriteView,
    LiveSearchView, UploadProductImageView, DeleteProductImageView,
    ProductDeleteView, ProductUpdateView,
    ReviewListView, ReviewCreateView,
    ProductVariantCreateView, LunchMenuView
)

app_name = 'products'

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('favorites/', FavoritesListView.as_view(), name='favorites'),
    path('<int:product_id>/favorite/', ToggleFavoriteView.as_view(), name='toggle-favorite'),
    path('<int:product_id>/favorite/check/', CheckFavoriteView.as_view(), name='check-favorite'),
    path('live-search/', LiveSearchView.as_view(), name='live-search'),
    path('<int:product_id>/upload-image/', UploadProductImageView.as_view(), name='upload-image'),
    path('<int:product_id>/delete-image/', DeleteProductImageView.as_view(), name='delete-image'),
    path('<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('<int:product_id>/reviews/', ReviewListView.as_view(), name='review-list'),
    path('<int:product_id>/reviews/create/', ReviewCreateView.as_view(), name='review-create'),
    path('<int:product_id>/variants/create/', ProductVariantCreateView.as_view(), name='variant-create'),
    path('lunch-menu/', LunchMenuView.as_view(), name='lunch-menu'),
]