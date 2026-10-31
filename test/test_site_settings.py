import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from core.models import SiteSettings
from users.models import User


@pytest.mark.django_db
def test_contact_address_can_be_blank():
    admin = User.objects.create_user(
        username='settings-admin',
        password='settings-password-123',
        phone='+79990000401',
        role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.put(
        '/api/v1/core/settings/',
        {'contact_address': ''},
        format='json',
    )

    assert response.status_code == 200, response.data
    assert response.data['contact_address'] == ''
    assert SiteSettings.get_settings().contact_address == ''
