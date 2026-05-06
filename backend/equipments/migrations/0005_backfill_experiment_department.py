"""Backfill ``Experiment.department`` from each experiment's first
required-equipment unit's lab.

Existing experiment rows were defined before the schema gained a direct
lab pointer; the lab can be inferred from where the equipment that the
recipe required actually lives. The first ``ExperimentRequiredEquipment``
(by ``step_order``) → its ``EquipmentType``'s first ``Equipment`` row →
that equipment's department wins.

Idempotent: ``filter(department__isnull=True)`` skips rows that already
have a lab assigned (manually or via subsequent edits).
"""
from django.db import migrations


def backfill_department(apps, schema_editor):
    Experiment = apps.get_model('equipments', 'Experiment')
    Equipment = apps.get_model('equipments', 'Equipment')

    for exp in Experiment.objects.filter(department__isnull=True):
        first_req = (
            exp.required_equipments
            .order_by('step_order', 'id')
            .first()
        )
        if first_req is None:
            continue
        first_eq = (
            Equipment.objects
            .filter(
                equipment_type_id=first_req.equipment_type_id,
                department__isnull=False,
            )
            .order_by('code')
            .first()
        )
        if first_eq is None:
            continue
        exp.department = first_eq.department
        exp.save(update_fields=['department'])


def reverse(apps, schema_editor):
    """No-op on rollback — never null out manually-assigned labs."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('equipments', '0004_experiment_department'),
    ]

    operations = [
        migrations.RunPython(backfill_department, reverse),
    ]
