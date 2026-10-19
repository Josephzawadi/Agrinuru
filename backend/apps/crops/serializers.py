from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Crop


class CropSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.farm_name", read_only=True)

    class Meta:
        model = Crop
        fields = [
            "id",
            "crop_name",
            "variety",
            "farm",
            "farm_name",
            "planting_date",
            "expected_harvest_date",
            "cultivated_area_acres",
            "growth_stage",
            "expected_harvest_quantity",
            "harvest_quantity_unit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "farm_name", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        crop = self.instance or Crop()
        for field, value in attrs.items():
            setattr(crop, field, value)

        try:
            crop.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

        return attrs