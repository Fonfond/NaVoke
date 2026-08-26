# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'role', 'bonus_points', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'phone', 'full_name')
    ordering = ('-date_joined',)
    
    # Поля для просмотра и редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'full_name', 'birth_date', 'avatar', 'bonus_points', 'role'),
        }),
    )
    
    # Поля для формы создания НОВОГО пользователя (это самое важное!)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone', 'full_name', 'password1', 'password2'),
        }),
    )