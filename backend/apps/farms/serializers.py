from rest_framework import serializers

from .models import Farm


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = [
            "id",
            "farmer",
            "farm_name",
            "location",
            "approximate_size_acres",
            "date_created",
        ]
        read_only_fields = ["id", "date_created"]