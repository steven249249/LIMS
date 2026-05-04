"""Auto-provision the system superuser on first migrate.

Runs once when the database is brought up to date. Skips silently if an
account with username ``admin`` already exists, so re-running migrations
or applying this on a database that was bootstrapped with seed_data.json
is a no-op.

Password sources, in order of precedence:
  1. ``LIMS_ADMIN_PASSWORD`` environment variable (set this in production)
  2. The default below — fine for dev, not safe to ship publicly

For an existing deployment that wants to rotate the password later, run:
    python manage.py ensure_admin --password '<new>'
"""
import os

from django.contrib.auth.hashers import make_password
from django.db import migrations

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'Admin@LIMS_2026!Sup'
DEFAULT_EMAIL = 'admin@lims.local'


def create_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')

    # Skip if anything already claims the username — don't clobber.
    if User.objects.filter(username=DEFAULT_USERNAME).exists():
        return

    password = os.environ.get('LIMS_ADMIN_PASSWORD') or DEFAULT_PASSWORD

    User.objects.create(
        username=DEFAULT_USERNAME,
        email=DEFAULT_EMAIL,
        first_name='System',
        last_name='Admin',
        role='superuser',
        status='active',
        is_staff=True,
        is_superuser=True,
        is_active=True,
        password=make_password(password),
    )


def reverse(apps, schema_editor):
    """No-op on rollback — never auto-delete the admin account.

    A migration rollback is rare and usually accidental; deleting the only
    remaining superuser would lock administrators out of their system.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse),
    ]
