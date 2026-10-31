from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_check_email_skips_non_network_backend(settings, capsys):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    call_command('check_email')

    output = capsys.readouterr().out
    assert 'non-network' in output


def test_check_email_reports_smtp_failure(settings, capsys):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    settings.EMAIL_HOST = 'smtp.invalid'
    settings.EMAIL_PORT = 465
    settings.EMAIL_USE_SSL = True
    settings.EMAIL_USE_TLS = False

    class BrokenConnection:
        def open(self):
            raise RuntimeError('connection refused')

        def close(self):
            pass

    with patch(
        'notifications.management.commands.check_email.get_connection',
        return_value=BrokenConnection(),
    ):
        with pytest.raises(CommandError):
            call_command('check_email')

    output = capsys.readouterr()
    assert 'SMTP connection: FAILED' in output.err


def test_check_email_reports_success(settings, capsys):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    settings.EMAIL_HOST = 'smtp.example.com'
    settings.EMAIL_PORT = 465
    settings.EMAIL_USE_SSL = True
    settings.EMAIL_USE_TLS = False

    class GoodConnection:
        def open(self):
            pass

        def close(self):
            pass

    with patch(
        'notifications.management.commands.check_email.get_connection',
        return_value=GoodConnection(),
    ):
        call_command('check_email')

    output = capsys.readouterr().out
    assert 'SMTP connection: OK' in output
