"""
equipments/serializers.py
"""
from rest_framework import serializers
from .models import Experiment, EquipmentType, Equipment, ExperimentRequiredEquipment


class EquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = ['id', 'name']


class EquipmentSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id', 'equipment_type', 'type_name', 'code', 'status',
            'department', 'department_name',
        ]


class ExperimentRequiredEquipmentSerializer(serializers.ModelSerializer):
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = ExperimentRequiredEquipment
        fields = ['id', 'experiment', 'equipment_type', 'equipment_type_name', 'quantity', 'department_name', 'step_order']

    def get_department_name(self, obj):
        # Infer department from the first equipment of this type
        first_eq = Equipment.objects.filter(equipment_type=obj.equipment_type).first()
        return first_eq.department.name if first_eq and first_eq.department else "N/A"


class ExperimentSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Experiment
        fields = ['id', 'name', 'remark', 'department', 'department_name']
