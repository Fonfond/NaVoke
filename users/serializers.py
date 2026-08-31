# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'full_name', 
                  'avatar', 'birth_date', 'bonus_points', 'role')
        read_only_fields = ('bonus_points', 'role', 'id')
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
            'phone': {'required': False},
        }


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('phone', 'full_name', 'password', 'password2')  # ✅ Убрали email, username

    def validate(self, attrs):
        # ✅ Проверка пароля
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Пароли не совпадают"})
        
        # ✅ Проверка телефона на уникальность
        phone = attrs.get('phone')
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "Пользователь с таким телефоном уже существует"})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        # ✅ Создаём username из телефона
        phone = validated_data['phone']
        username = phone.replace('+', '').replace(' ', '').replace('-', '')
        user = User.objects.create_user(username=username, **validated_data)
        return user
