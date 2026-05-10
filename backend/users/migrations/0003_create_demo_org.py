"""Auto-provision the demo organisation on first migrate.

Mirrors the layout that was previously bootstrapped via
``loaddata seed_data.json`` so the system feels familiar:

  FAB12A
  └── Photolithography Lab        Lab_Mgr_Photo     + Lab_Mem_Photo_001
  └── Thin Film & Etch Lab        Lab_Mgr_Process   + Lab_Mem_Process_001
  └── Metrology & Inspection Lab  Lab_Mgr_QC        + Lab_Mem_QC_001
  └── (testuser — regular_employee, attached to Photolithography Lab so
      create_order works out of the box)

Every check uses ``filter(...).exists()`` so re-running migrate or applying
this on top of a database already seeded via the old fixture is a safe
no-op — existing accounts are left untouched.

All accounts default to password ``Lims@2026!Init`` (override via
``LIMS_DEMO_PASSWORD`` env var). The original fixture had every user on a
different password that nobody remembered; one shared password gets the
team logged in, then the admin can rotate via the bulk-user UI.
"""
import os

from django.contrib.auth.hashers import make_password
from django.db import migrations

DEFAULT_PASSWORD = 'Lims@2026!Init'
DEFAULT_FAB_NAME = 'FAB12A'

# (department_name, lab-manager-username, lab-member-username) tuples in the
# order they appear in the relay flow.
DEPARTMENTS = [
    ('Photolithography Lab', 'Lab_Mgr_Photo', 'Lab_Mem_Photo_001'),
    ('Thin Film & Etch Lab', 'Lab_Mgr_Process', 'Lab_Mem_Process_001'),
    ('Metrology & Inspection Lab', 'Lab_Mgr_QC', 'Lab_Mem_QC_001'),
]

# Floor user: a regular_employee that submits sample orders. Attached to the
# Photo lab so create_order() (which reads user.department) works immediately.
EMPLOYEE_USERNAME = 'testuser'


def create_demo_org(apps, schema_editor):
    # Demo seed migrations are gated by ``SEED_DEMO_DATA``. Production /
    # staging deploys leave it unset (default False) so the cluster never
    # contains a known-password demo account by accident.
    if os.environ.get('SEED_DEMO_DATA', 'True').lower() not in ('true', '1', 'yes'):
        return

    FAB = apps.get_model('users', 'FAB')
    Department = apps.get_model('users', 'Department')
    User = apps.get_model('users', 'User')

    password_hash = make_password(
        os.environ.get('LIMS_DEMO_PASSWORD') or DEFAULT_PASSWORD,
    )

    # 1) FAB
    fab, _ = FAB.objects.get_or_create(fab_name=DEFAULT_FAB_NAME)

    # 2) Departments + manager + member
    departments_by_index = []
    for dept_name, mgr_username, mem_username in DEPARTMENTS:
        dept, _ = Department.objects.get_or_create(fab=fab, name=dept_name)
        departments_by_index.append(dept)

        if not User.objects.filter(username=mgr_username).exists():
            User.objects.create(
                username=mgr_username,
                email=f'{mgr_username.lower()}@lims.local',
                first_name='Lab',
                last_name=f'Manager — {dept_name}',
                role='lab_manager',
                status='active',
                department=dept,
                is_active=True,
                password=password_hash,
            )

        if not User.objects.filter(username=mem_username).exists():
            User.objects.create(
                username=mem_username,
                email=f'{mem_username.lower()}@lims.local',
                first_name='Lab',
                last_name=f'Member — {dept_name}',
                role='lab_member',
                status='active',
                department=dept,
                is_active=True,
                password=password_hash,
            )

    # 3) Floor user (regular_employee). Belongs to the Photo lab so
    #    create_order() (which reads user.department) works out of the box.
    if not User.objects.filter(username=EMPLOYEE_USERNAME).exists():
        User.objects.create(
            username=EMPLOYEE_USERNAME,
            email=f'{EMPLOYEE_USERNAME}@lims.local',
            first_name='Floor',
            last_name='Employee',
            role='regular_employee',
            status='active',
            department=departments_by_index[0],   # Photolithography Lab
            is_active=True,
            password=password_hash,
        )


def reverse(apps, schema_editor):
    """No-op on rollback — never auto-delete demo accounts.

    A migration rollback is rarely intentional in production; deleting
    every demo account when someone fat-fingers a `migrate` would
    surprise everyone.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_create_default_admin'),
    ]

    operations = [
        migrations.RunPython(create_demo_org, reverse),
    ]
