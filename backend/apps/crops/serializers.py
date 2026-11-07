from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.roles import is_agrinuru_staff
from apps.farms.models import Farm

from .models import Crop


class CropSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.farm_name", read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and not request.user.is_superuser
            and not is_agrinuru_staff(request.user)
        ):
            self.fields["farm"].queryset = Farm.objects.filter(
                farmer__user=request.user
            )

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