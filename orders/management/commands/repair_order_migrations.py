from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


MIGRATION_0009 = '0009_order_order_total_amount_non_negative_and_more'
MIGRATION_0010 = '0010_orderstatushistory'

ORDER_0009_CONSTRAINTS = {
    'order_total_amount_non_negative',
    'order_bonus_used_non_negative',
}

ORDER_0010_COLUMNS = {
    'id',
    'order_id',
    'from_status',
    'to_status',
    'changed_by_id',
    'created_at',
}


def missing_order_0009(existing_constraints):
    return ORDER_0009_CONSTRAINTS - set(existing_constraints)


def missing_order_0010(existing_columns):
    return ORDER_0010_COLUMNS - set(existing_columns)


class Command(BaseCommand):
    help = (
        'Repair the orders.0009/0010 migration state when the schema already '
        'exists but django_migrations has no record. Never fakes a partial schema.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be done.',
        )

    def _migration_applied(self, name):
        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return False
        return recorder.migration_qs.filter(app='orders', name=name).exists()

    def _order_constraints(self):
        tables = connection.introspection.table_names()
        if 'orders' not in tables:
            return set()
        with connection.cursor() as cursor:
            return set(
                connection.introspection.get_constraints(
                    cursor,
                    'orders',
                ).keys()
            )

    def _history_columns(self):
        tables = connection.introspection.table_names()
        if 'order_status_history' not in tables:
            return None
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                'order_status_history',
            )
        return {column.name for column in description}

    def _fake(self, name, dry_run):
        if dry_run:
            self.stdout.write(f'orders.{name}: would be faked')
            return
        call_command(
            'migrate',
            'orders',
            name,
            '--fake',
            verbosity=0,
        )
        self.stdout.write(
            self.style.SUCCESS(f'orders.{name}: fake applied')
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        constraints = self._order_constraints()
        missing_0009 = missing_order_0009(constraints)
        applied_0009 = self._migration_applied(MIGRATION_0009)

        if applied_0009:
            self.stdout.write('orders.0009: already recorded')
        elif not constraints:
            self.stdout.write(
                'orders.0009: schema absent, normal migrate will create it'
            )
        elif missing_0009:
            raise CommandError(
                'orders.0009: schema is partial, missing constraints: '
                + ', '.join(sorted(missing_0009))
                + '. Refusing to fake; inspect the database.'
            )
        else:
            self._fake(MIGRATION_0009, dry_run)

        columns = self._history_columns()
        applied_0010 = self._migration_applied(MIGRATION_0010)

        if applied_0010:
            self.stdout.write('orders.0010: already recorded')
        elif columns is None:
            self.stdout.write(
                'orders.0010: schema absent, normal migrate will create it'
            )
        else:
            missing_0010 = missing_order_0010(columns)
            if missing_0010:
                raise CommandError(
                    'orders.0010: order_status_history is partial, missing '
                    'columns: '
                    + ', '.join(sorted(missing_0010))
                    + '. Refusing to fake; inspect the database.'
                )
            self._fake(MIGRATION_0010, dry_run)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: no migrations were changed')
            )
