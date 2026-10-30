# users/serializers.py
from django.db import IntegrityError
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .utils import InvalidPhoneError, normalize_phone, try_normalize_phone


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

    def validate_phone(self, value):
        try:
            phone = normalize_phone(value)
        except InvalidPhoneError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        queryset = User.objects.filter(phone=phone)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                'Пользователь с таким телефоном уже существует'
            )

        return phone


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

        try:
            phone = normalize_phone(attrs.get('phone', ''))
        except InvalidPhoneError as exc:
            raise serializers.ValidationError({"phone": str(exc)}) from exc

        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                {"phone": "Пользователь с таким телефоном уже существует"}
            )
        if User.objects.filter(username=phone).exists():
            raise serializers.ValidationError(
                {"phone": "Этот телефон уже используется"}
            )

        attrs['phone'] = phone
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        phone = validated_data.pop('phone')

        try:
            return User.objects.create_user(
                username=phone,
                phone=phone,
                **validated_data,
            )
        except IntegrityError as exc:
            # Гонка двух одновременных регистраций с одним телефоном.
            raise serializers.ValidationError(
                {"phone": "Пользователь с таким телефоном уже существует"}
            ) from exc


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Логин по username или телефону в любом формате."""

    def validate(self, attrs):
        raw_username = attrs.get(self.username_field)
        normalized = try_normalize_phone(raw_username)

        if normalized:
            attrs[self.username_field] = normalized

        try:
            return super().validate(attrs)
        except AuthenticationFailed:
            # Старые пользователи могли иметь username вида 7(999)1234567,
            # либо телефон менялся в профиле без смены username.
            if normalized:
                user = User.objects.filter(phone=normalized).first()
                if user:
                    attrs[self.username_field] = user.username
                    return super().validate(attrs)
            raise
