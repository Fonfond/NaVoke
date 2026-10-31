from unittest.mock import patch

import pytest
from django.core.management.base import CommandError

from orders.management.commands.repair_order_migrations import (
    ORDER_0009_CONSTRAINTS,
    ORDER_0010_COLUMNS,
    Command as RepairCommand,
    missing_order_0009,
    missing_order_0010,
)


def test_missing_constraints_detection():
    assert missing_order_0009(set()) == ORDER_0009_CONSTRAINTS
    assert missing_order_0009(ORDER_0009_CONSTRAINTS) == set()
    assert missing_order_0009({'order_total_amount_non_negative'}) == {
        'order_bonus_used_non_negative'
    }


def test_missing_columns_detection():
    assert missing_order_0010(set()) == ORDER_0010_COLUMNS
    assert missing_order_0010(ORDER_0010_COLUMNS) == set()


@pytest.mark.django_db
def test_repair_fakes_only_complete_schema():
    command = RepairCommand()
    with patch.object(command, '_migration_applied', side_effect=[False, False]), \
         patch.object(command, '_order_constraints', return_value=ORDER_0009_CONSTRAINTS), \
         patch.object(command, '_history_columns', return_value=ORDER_0010_COLUMNS), \
         patch(
             'orders.management.commands.repair_order_migrations.call_command'
         ) as fake_migrate:
        command.handle(dry_run=False)

    assert fake_migrate.call_count == 2


@pytest.mark.django_db
def test_repair_refuses_partial_schema():
    command = RepairCommand()
    with patch.object(command, '_migration_applied', return_value=False), \
         patch.object(command, '_order_constraints', return_value={
             'order_total_amount_non_negative',
         }):
        with pytest.raises(CommandError, match='partial'):
            command.handle(dry_run=False)


@pytest.mark.django_db
def test_repair_dry_run_does_not_migrate():
    command = RepairCommand()
    with patch.object(command, '_migration_applied', return_value=False), \
         patch.object(command, '_order_constraints', return_value=ORDER_0009_CONSTRAINTS), \
         patch.object(command, '_history_columns', return_value=ORDER_0010_COLUMNS), \
         patch(
             'orders.management.commands.repair_order_migrations.call_command'
         ) as fake_migrate:
        command.handle(dry_run=True)

    fake_migrate.assert_not_called()
