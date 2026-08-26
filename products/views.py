# products/views.py
import os
from rest_framework import generics, filters, permissions, status, serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Category, Product, LunchMenu, ProductVariant, Favorite, Review
from .serializers import CategorySerializer, LunchMenuSerializer, ProductSerializer, FavoriteSerializer, ReviewSerializer, ProductVariantSerializer


class CategoryListView(generics.ListAPIView):
    """Список всех категорий"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)


class ProductListView(generics.ListCreateAPIView):
    """Список всех товаров + создание"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_hit', 'is_new']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут создавать товары'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


class ProductDetailView(generics.RetrieveAPIView):
    """Детальная информация о товаре (с вариациями)"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (permissions.AllowAny,)


class ToggleFavoriteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        favorite = Favorite.objects.filter(user=request.user, product=product).first()
        if favorite:
            favorite.delete()
            return Response({'status': 'removed', 'message': 'Товар удалён из избранного'}, status=status.HTTP_200_OK)
        else:
            Favorite.objects.create(user=request.user, product=product)
            return Response({'status': 'added', 'message': 'Товар добавлен в избранное'}, status=status.HTTP_201_CREATED)


class FavoritesListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = FavoriteSerializer
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)


class CheckFavoriteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, product_id):
        is_favorite = Favorite.objects.filter(user=request.user, product_id=product_id).exists()
        return Response({'is_favorite': is_favorite})


class LiveSearchView(APIView):
    permission_classes = (permissions.AllowAny,)
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 10))
        if not query:
            return Response([])
        products = Product.objects.filter(name__icontains=query)[:limit]
        data = [{
            'id': p.id,
            'name': p.name,
            'price': (
                str(p.variants.filter(is_available=True).order_by('price').first().price)
                if p.variants.exists()
                else (str(p.price) if p.price else '0')
            ),
            'image_url': p.image_url,
            'category_name': p.category.name if p.category else None
        } for p in products]
        return Response(data)


class LunchMenuView(APIView):
    """Получение и сохранение меню бизнес-ланча"""
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request):
        # ✅ Ищем последнее активное меню
        menu = LunchMenu.objects.filter(is_active=True).order_by('-date').first()
        if not menu:
            return Response({'items': [], 'title': 'Бизнес-ланч'})
        serializer = LunchMenuSerializer(menu)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут сохранять меню'}, status=403)
        
        today = timezone.now().date()
        data = request.data
        title = data.get('title', 'Бизнес-ланч')
        raw_items = data.get('items', [])
        
        # ✅ АВТОМАТИЧЕСКОЕ ПРИСВОЕНИЕ ID
        items = []
        for item in raw_items:
            name = item.get('name', '').strip()
            price = item.get('price', 0)
            product_id = item.get('product_id')  # Может быть None
            
            # ✅ ЕСЛИ ID НЕ УКАЗАН — ИЩЕМ ТОВАР ПО НАЗВАНИЮ
            if not product_id:
                # Ищем товар с похожим названием
                product = Product.objects.filter(name__icontains=name).first()
                if product:
                    product_id = product.id
                    print(f"✅ Найден товар: {name} (ID: {product_id})")
                else:
                    # ✅ ЕСЛИ ТОВАР НЕ НАЙДЕН — СОЗДАЁМ НОВЫЙ
                    category = Category.objects.first()
                    if not category:
                        category = Category.objects.create(
                            name='Бизнес-ланч',
                            slug='business-lunch'
                        )
                    
                    product = Product.objects.create(
                        name=name,
                        category=category,
                        price=price,
                        weight=0,
                        has_variants=False,
                        is_new=True
                    )
                    product_id = product.id
                    print(f"✅ Создан новый товар: {name} (ID: {product_id})")
            
            items.append({
                'name': name,
                'price': price,
                'product_id': product_id
            })
        
        # ✅ Сохраняем меню с обновлёнными items
        menu, created = LunchMenu.objects.update_or_create(
            date=today,
            defaults={'title': title, 'items': items, 'is_active': True}
        )
        
        serializer = LunchMenuSerializer(menu)
        return Response(serializer.data, status=201)

class UploadProductImageView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, product_id):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут загружать фото'}, status=status.HTTP_403_FORBIDDEN)
        product = get_object_or_404(Product, id=product_id)
        if 'image' not in request.FILES:
            return Response({'error': 'Файл изображения не найден'}, status=status.HTTP_400_BAD_REQUEST)
        file = request.FILES['image']
        if file.size > 5 * 1024 * 1024:
            return Response({'error': 'Размер файла не должен превышать 5 МБ'}, status=status.HTTP_400_BAD_REQUEST)
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
        if file.content_type not in allowed_types:
            return Response({'error': f'Поддерживаются только: {", ".join(allowed_types)}'}, status=status.HTTP_400_BAD_REQUEST)
        product.image = file
        product.save()
        return Response({'success': True, 'message': 'Изображение загружено', 'image_url': product.image.url if product.image else None}, status=status.HTTP_200_OK)


class DeleteProductImageView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def delete(self, request, product_id):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут удалять фото'}, status=status.HTTP_403_FORBIDDEN)
        product = get_object_or_404(Product, id=product_id)
        if product.image:
            if os.path.isfile(product.image.path):
                os.remove(product.image.path)
            product.image = None
            product.save()
            return Response({'success': True, 'message': 'Изображение удалено'}, status=status.HTTP_200_OK)
        return Response({'error': 'Изображение не найдено'}, status=status.HTTP_404_NOT_FOUND)


class ProductDeleteView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticated,)
    def delete(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут удалять товары'}, status=status.HTTP_403_FORBIDDEN)
        product = self.get_object()
        from orders.models import CartItem, OrderItem
        CartItem.objects.filter(product=product).delete()
        OrderItem.objects.filter(product=product).delete()
        Favorite.objects.filter(product=product).delete()
        product.delete()
        return Response({'message': f'Товар #{product.id} успешно удалён'}, status=status.HTTP_200_OK)


class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticated,)
    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут редактировать товары'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class ReviewCreateView(generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated,)
    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        if Review.objects.filter(product=product, user=self.request.user).exists():
            return Response({'detail': 'Вы уже оставили отзыв на этот товар.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(user=self.request.user, product=product)


class ReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (permissions.AllowAny,)
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return Review.objects.filter(product_id=product_id, is_approved=True)


class ProductVariantCreateView(generics.CreateAPIView):
    """Создание вариации для товара (только для админов)"""
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied('Только администраторы могут создавать вариации')
        product_id = self.kwargs.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        serializer.save(product=product)