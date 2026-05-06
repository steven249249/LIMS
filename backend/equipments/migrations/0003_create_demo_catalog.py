"""Auto-provision the demo equipment catalogue + experiment library.

A simplified TSMC-style wafer fab: 12 tool types, 24 equipment units across
the three labs, and 6 experiments covering FEOL → BEOL → Test.

Equipment types (12)
    Photolithography:    EUV Scanner, Track System
    Thin Film & Etch:    ALD, PVD Sputter, Furnace, Dry Etcher,
                         CMP Polisher, Wet Bench, Ion Implanter
    Metrology / Test:    CD-SEM, Inspect Tool, Auto Prober

Equipment units (24) attached to the three labs:
    Photolithography Lab          EUV-001/002, TRACK-001/002
    Thin Film & Etch Lab          ALD-001/002, PVD-001/002, FURN-001,
                                  ETCH-001/002, CMP-001/002, WET-001,
                                  IMP-001
    Metrology & Inspection Lab    CDSEM-001/002/003, INSP-001/002,
                                  PROBE-001/002/003

Experiments + per-step equipment requirements (6 experiments)
    Full Litho & Metrology Process       (光刻 + 量測)
        Track System → EUV Scanner → CD-SEM
    Surface Planarization & Inspect      (CMP 平坦化)
        CMP Polisher → Inspect Tool
    Thin Film & Etch Loop                (薄膜沉積 + 蝕刻)
        ALD → Dry Etcher → Inspect Tool
    Ion Implant & Anneal Cycle           (離子佈植 + 退火,FEOL)
        Ion Implanter → Furnace → CD-SEM
    Metal Layer Build (BEOL)             (金屬層,後段製程)
        PVD Sputter → CMP Polisher → Inspect Tool
    Final Device Testing                 (出廠測試)
        Auto Prober → Inspect Tool

Idempotent: every check uses ``get_or_create`` / ``filter(...).exists()``
so re-running migrate, applying on top of a database already seeded via
the legacy fixture, or stacking migrations all leave existing rows alone.
"""
from django.db import migrations


# (name)
EQUIPMENT_TYPES = [
    # Photolithography
    'EUV Scanner', 'Track System',
    # Thin Film & Etch (FEOL + parts of BEOL)
    'ALD', 'PVD Sputter', 'Furnace', 'Dry Etcher',
    'CMP Polisher', 'Wet Bench', 'Ion Implanter',
    # Metrology & Inspection / Test
    'CD-SEM', 'Inspect Tool', 'Auto Prober',
]

# (code, type_name, department_name, status)
EQUIPMENT_INSTANCES = [
    # ── Photolithography Lab ──────────────────────────────────────────
    ('EUV-001', 'EUV Scanner', 'Photolithography Lab', 'available'),
    ('EUV-002', 'EUV Scanner', 'Photolithography Lab', 'available'),
    ('TRACK-001', 'Track System', 'Photolithography Lab', 'available'),
    ('TRACK-002', 'Track System', 'Photolithography Lab', 'available'),
    # ── Thin Film & Etch Lab ──────────────────────────────────────────
    ('ALD-001', 'ALD', 'Thin Film & Etch Lab', 'available'),
    ('ALD-002', 'ALD', 'Thin Film & Etch Lab', 'occupied'),
    ('PVD-001', 'PVD Sputter', 'Thin Film & Etch Lab', 'available'),
    ('PVD-002', 'PVD Sputter', 'Thin Film & Etch Lab', 'available'),
    ('FURN-001', 'Furnace', 'Thin Film & Etch Lab', 'available'),
    ('ETCH-001', 'Dry Etcher', 'Thin Film & Etch Lab', 'available'),
    ('ETCH-002', 'Dry Etcher', 'Thin Film & Etch Lab', 'available'),
    ('CMP-001', 'CMP Polisher', 'Thin Film & Etch Lab', 'available'),
    ('CMP-002', 'CMP Polisher', 'Thin Film & Etch Lab', 'available'),
    ('WET-001', 'Wet Bench', 'Thin Film & Etch Lab', 'available'),
    ('IMP-001', 'Ion Implanter', 'Thin Film & Etch Lab', 'available'),
    # ── Metrology & Inspection Lab ────────────────────────────────────
    ('CDSEM-001', 'CD-SEM', 'Metrology & Inspection Lab', 'available'),
    ('CDSEM-002', 'CD-SEM', 'Metrology & Inspection Lab', 'available'),
    ('CDSEM-003', 'CD-SEM', 'Metrology & Inspection Lab', 'available'),
    ('INSP-001', 'Inspect Tool', 'Metrology & Inspection Lab', 'available'),
    ('INSP-002', 'Inspect Tool', 'Metrology & Inspection Lab', 'available'),
    ('PROBE-001', 'Auto Prober', 'Metrology & Inspection Lab', 'available'),
    ('PROBE-002', 'Auto Prober', 'Metrology & Inspection Lab', 'available'),
    ('PROBE-003', 'Auto Prober', 'Metrology & Inspection Lab', 'available'),
]

# (experiment_name, remark, [(step_order, equipment_type, quantity), ...])
EXPERIMENTS = [
    (
        'Full Litho & Metrology Process',
        '光刻製程:塗光阻 → EUV 曝光 → CD-SEM 量測線寬。',
        [
            (1, 'Track System', 1),
            (2, 'EUV Scanner', 1),
            (3, 'CD-SEM', 1),
        ],
    ),
    (
        'Surface Planarization & Inspect',
        'CMP 化學機械研磨晶圓平坦化,再做光學表面檢測。',
        [
            (1, 'CMP Polisher', 1),
            (2, 'Inspect Tool', 1),
        ],
    ),
    (
        'Thin Film & Etch Loop',
        '薄膜製程:原子層沉積 → 乾式蝕刻定義圖案 → 缺陷檢測。',
        [
            (1, 'ALD', 1),
            (2, 'Dry Etcher', 1),
            (3, 'Inspect Tool', 1),
        ],
    ),
    (
        'Ion Implant & Anneal Cycle',
        'FEOL 摻雜製程:離子佈植 → 高溫爐管退火 → 線寬量測確認。',
        [
            (1, 'Ion Implanter', 1),
            (2, 'Furnace', 1),
            (3, 'CD-SEM', 1),
        ],
    ),
    (
        'Metal Layer Build (BEOL)',
        '後段金屬層:PVD 濺鍍金屬 → CMP 平坦化 → 表面檢測。',
        [
            (1, 'PVD Sputter', 1),
            (2, 'CMP Polisher', 1),
            (3, 'Inspect Tool', 1),
        ],
    ),
    (
        'Final Device Testing',
        '完工晶圓測試:自動針測 → 最終缺陷檢查。',
        [
            (1, 'Auto Prober', 1),
            (2, 'Inspect Tool', 1),
        ],
    ),
]


def create_demo_catalog(apps, schema_editor):
    EquipmentType = apps.get_model('equipments', 'EquipmentType')
    Equipment = apps.get_model('equipments', 'Equipment')
    Experiment = apps.get_model('equipments', 'Experiment')
    ExperimentRequiredEquipment = apps.get_model(
        'equipments', 'ExperimentRequiredEquipment',
    )
    Department = apps.get_model('users', 'Department')

    # 1) Equipment types
    types_by_name = {}
    for name in EQUIPMENT_TYPES:
        et, _ = EquipmentType.objects.get_or_create(name=name)
        types_by_name[name] = et

    # 2) Department lookup (created earlier by users.0003_create_demo_org)
    departments_by_name = {d.name: d for d in Department.objects.all()}

    # 3) Equipment instances
    for code, type_name, dept_name, status in EQUIPMENT_INSTANCES:
        if Equipment.objects.filter(code=code).exists():
            continue
        dept = departments_by_name.get(dept_name)
        if dept is None:
            # Should never happen — the users migration runs first via the
            # dependency below, so the lab is guaranteed to exist.
            continue
        Equipment.objects.create(
            code=code,
            equipment_type=types_by_name[type_name],
            department=dept,
            status=status,
        )

    # 4) Experiments + per-step equipment requirements. ``department`` is
    #    not set here because the field doesn't exist yet at this point in
    #    migration history — the later 0005_backfill_experiment_department
    #    migration walks each experiment's first required-equipment row
    #    and points it at that lab.
    for exp_name, remark, steps in EXPERIMENTS:
        exp, _ = Experiment.objects.get_or_create(
            name=exp_name,
            defaults={'remark': remark},
        )
        for step_order, type_name, quantity in steps:
            equipment_type = types_by_name[type_name]
            if ExperimentRequiredEquipment.objects.filter(
                experiment=exp, equipment_type=equipment_type,
            ).exists():
                continue
            ExperimentRequiredEquipment.objects.create(
                experiment=exp,
                equipment_type=equipment_type,
                step_order=step_order,
                quantity=quantity,
            )


def reverse(apps, schema_editor):
    """No-op on rollback — never auto-delete demo catalogue rows."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('equipments', '0002_equipment_department_and_more'),
        ('users', '0003_create_demo_org'),  # Departments must exist first
    ]

    operations = [
        migrations.RunPython(create_demo_catalog, reverse),
    ]
