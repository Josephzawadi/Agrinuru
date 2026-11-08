from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import FarmerProfile, validate_phone_number
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


class FarmerProfileAccountLinkSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=True,
    )

    class Meta:
        model = FarmerProfile
        fields = ["user"]

    def validate_user(self, user):
        if user is not None and FarmerProfile.objects.filter(user=user).exclude(
            pk=self.instance.pk
        ).exists():
            raise serializers.ValidationError("This account is already linked to a farmer profile.")
        return user


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
    full_name = serializers.CharField(max_length=150, trim_whitespace=True)
    phone_number = serializers.CharField(
        max_length=30,
        trim_whitespace=True,
        validators=[validate_phone_number],
    )
    county = serializers.CharField(max_length=100, trim_whitespace=True)
    sub_county = serializers.CharField(max_length=100, trim_whitespace=True)
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

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        FarmerProfile.objects.create(
            user=user,
            full_name=validated_data["full_name"],
            phone_number=validated_data["phone_number"],
            email=user.email,
            county=validated_data["county"],
            sub_county=validated_data["sub_county"],
        )
        return user


class StaffAssignmentSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()