"""
Serializers for authentication endpoints — design_doc §4.1
Login: username + password → access token, refresh token, user info.
"""
from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.authentication.models import User


class LoginSerializer(serializers.Serializer):
    """design_doc §4.1 POST /api/v1/auth/login/ request body."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        data["user"] = user
        return data


class UserSummarySerializer(serializers.ModelSerializer):
    """Minimal user info returned inside the login response."""
    class Meta:
        model = User
        fields = ["id", "username", "role"]


class UserSerializer(serializers.ModelSerializer):
    """Full user serializer for Admin user-management endpoints (design_doc §4.4)."""
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
