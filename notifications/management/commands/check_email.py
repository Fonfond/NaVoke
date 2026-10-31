from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError

from notifications.task import _send_one


class Command(BaseCommand):
    help = (
        'Check SMTP settings and connection. With --send, also send a test '
        'email to ADMIN_EMAIL.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--send',
            action='store_true',
            help='Send a test email to ADMIN_EMAIL after a successful check.',
        )

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f'EMAIL_BACKEND={backend}')
        self.stdout.write(f'EMAIL_HOST={settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_SSL={settings.EMAIL_USE_SSL}')
        self.stdout.write(f'EMAIL_USE_TLS={settings.EMAIL_USE_TLS}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL={settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'ADMIN_EMAIL={settings.ADMIN_EMAIL}')

        if any(
            name in backend
            for name in (
                'locmem.EmailBackend',
                'console.EmailBackend',
                'dummy.EmailBackend',
            )
        ):
            self.stdout.write(self.style.WARNING(
                'Email backend is non-network; SMTP connection check skipped.'
            ))
            return

        connection = get_connection()
        try:
            connection.open()
            self.stdout.write(self.style.SUCCESS('SMTP connection: OK'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(
                f'SMTP connection: FAILED ({exc})'
            ))
            raise CommandError('SMTP check failed') from exc
        finally:
            try:
                connection.close()
            except Exception:
                pass

        if options['send']:
            sent = _send_one(
                'НаVoke SMTP test',
                'Это тестовое письмо от NaVoke. SMTP настроен корректно.',
                settings.ADMIN_EMAIL,
            )
            if not sent:
                raise CommandError('SMTP test email failed')
            self.stdout.write(
                f'Test email processed for {settings.ADMIN_EMAIL}'
            )
