"""Pre-populate a few wafer lots for the demo FAB.

The submission form uses a dropdown sourced from WaferLot, so the system
needs at least one lot per fab to be usable out of the box. Idempotent:
re-running migrate or applying on top of a database that already has the
codes is a no-op.
"""
from django.db import migrations


DEMO_LOTS = [
    # (fab_name, lot_code, notes)
    ('FAB12A', 'LOT-2026-A001', '12-inch wafer batch — pilot run'),
    ('FAB12A', 'LOT-2026-A002', '12-inch wafer batch — pilot run'),
    ('FAB12A', 'LOT-2026-A003', '12-inch wafer batch — pilot run'),
    ('FAB12A', 'LOT-2026-B001', 'BEOL test wafers'),
    ('FAB12A', 'LOT-2026-B002', 'BEOL test wafers'),
    ('FAB12A', 'LOT-2026-Q001', 'Engineering split – metrology only'),
]


def seed(apps, schema_editor):
    import os
    # Gated by the same SEED_DEMO_DATA env var as the other demo migrations.
    if os.environ.get('SEED_DEMO_DATA', 'True').lower() not in ('true', '1', 'yes'):
        return

    FAB = apps.get_model('users', 'FAB')
    WaferLot = apps.get_model('users', 'WaferLot')

    for fab_name, code, notes in DEMO_LOTS:
        try:
            fab = FAB.objects.get(fab_name=fab_name)
        except FAB.DoesNotExist:
            # FAB12A is created by users.0003_create_demo_org which runs
            # earlier; if it's missing the deployment is in an unusual
            # state and seeding is the wrong fix.
            continue
        WaferLot.objects.get_or_create(
            code=code, defaults={'fab': fab, 'notes': notes},
        )


def reverse(apps, schema_editor):
    """No-op on rollback — never auto-delete demo lot rows."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_waferlot'),
    ]

    operations = [
        migrations.RunPython(seed, reverse),
    ]
