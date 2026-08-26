# users/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSerializer, RegisterSerializer
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_fcm_token(request):
    token = request.data.get('fcm_token')
    if token:
        request.user.fcm_token = token
        request.user.save()
        return Response({'status': 'success'})
    return Response({'error': 'Token not provided'}, status=400)


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и редактирование профиля"""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    # ✅ Добавляем метод update для корректного обновления
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    """Список всех пользователей (только для админов)"""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return User.objects.none()
        return User.objects.all().order_by('-date_joined')


class UpdateUserRoleView(APIView):
    """Обновление роли пользователя (только для админов)"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def put(self, request, user_id):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять роли'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        role = request.data.get('role')
        if role not in ['client', 'manager', 'admin']:
            return Response(
                {'error': 'Недопустимая роль'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = role
        user.save()
        
        return Response(UserSerializer(user).data)


class ToggleUserStatusView(APIView):
    """Блокировка/разблокировка пользователя"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def put(self, request, user_id):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут блокировать пользователей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        is_active = request.data.get('is_active', True)
        user.is_active = is_active
        user.save()
        
        return Response(UserSerializer(user).data)