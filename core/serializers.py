# core/serializers.py
from rest_framework import serializers
from .models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    contact_address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=False,
    )

    class Meta:
        model = SiteSettings
        fields = '__all__'