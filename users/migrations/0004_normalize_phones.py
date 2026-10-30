import re

from django.db import migrations


def _normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')

    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits

    if len(digits) != 11 or not digits.startswith('7'):
        return None

    return digits


def forwards(apps, schema_editor):
    User = apps.get_model('users', 'User')
    db_alias = schema_editor.connection.alias
    users = list(User.objects.using(db_alias).all())

    normalized = {}
    seen = {}

    # Сначала проверяем все номера, чтобы не оставить БД в полу-мигрированном виде.
    for user in users:
        if not user.phone:
            continue
        phone = _normalize_phone(user.phone)
        if not phone:
            continue
        if phone in seen:
            raise RuntimeError(
                'Duplicate normalized phone {}: users {} and {}. '
                'Merge them manually before applying this migration.'.format(
                    phone, seen[phone], user.pk,
                )
            )
        seen[phone] = user.pk
        normalized[user.pk] = phone

    for user in users:
        phone = normalized.get(user.pk)
        if not phone:
            continue

        updates = {}
        if user.phone != phone:
            updates['phone'] = phone

        username_digits = re.sub(r'\D', '', user.username or '')
        if username_digits == phone and user.username != phone:
            conflict = (
                User.objects.using(db_alias)
                .filter(username=phone)
                .exclude(pk=user.pk)
                .exists()
            )
            if not conflict:
                updates['username'] = phone

        if updates:
            for field, value in updates.items():
                setattr(user, field, value)
            user.save(using=db_alias, update_fields=list(updates))


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_fcm_token'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
