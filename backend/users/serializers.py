"""
users/serializers.py
Serializers for authentication and user management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FAB, Department, WaferLot

User = get_user_model()


class FABSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAB
        fields = ['id', 'fab_name']


class DepartmentSerializer(serializers.ModelSerializer):
    fab_name = serializers.CharField(source='fab.fab_name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'fab', 'fab_name', 'name']


class WaferLotSerializer(serializers.ModelSerializer):
    fab_name = serializers.CharField(source='fab.fab_name', read_only=True)

    class Meta:
        model = WaferLot
        fields = ['id', 'fab', 'fab_name', 'code', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField()


    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'role',
            'department', 'department_name', 'status', 'joined_at',
        ]
        read_only_fields = ['id', 'joined_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only serializer for the currently logged-in user."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    fab_name = serializers.CharField(source='department.fab.fab_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'department_name', 'fab_name',
            'status', 'joined_at',
        ]
