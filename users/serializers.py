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
        # ✅ ДЕЛАЕМ ВСЕ ПОЛЯ НЕОБЯЗАТЕЛЬНЫМИ ДЛЯ РЕДАКТИРОВАНИЯ
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
        fields = ('username', 'email', 'phone', 'full_name', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user