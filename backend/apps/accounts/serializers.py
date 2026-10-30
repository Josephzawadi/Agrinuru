from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import FarmerProfile
from .roles import get_user_role, has_farmer_profile

User = get_user_model()


class FarmerProfileSerializer(serializers.ModelSerializer):
    preferred_language = serializers.CharField(
        max_length=50,
        allow_blank=False,
        trim_whitespace=True,
        required=True,
    )

    class Meta:
        model = FarmerProfile
        fields = [
            "id",
            "full_name",
            "phone_number",
            "email",
            "county",
            "sub_county",
            "preferred_language",
            "date_registered",
        ]
        read_only_fields = ["id", "date_registered"]


class AccountSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    has_farmer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "has_farmer_profile"]
        read_only_fields = fields

    def get_role(self, user):
        return get_user_role(user)

    def get_has_farmer_profile(self, user):
        return has_farmer_profile(user)


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_username(self, value):
        user_field = User._meta.get_field("username")
        try:
            user_field.run_validators(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error

        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        user = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class StaffAssignmentSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()