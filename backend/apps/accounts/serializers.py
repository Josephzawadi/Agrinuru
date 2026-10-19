from rest_framework import serializers

from .models import FarmerProfile


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