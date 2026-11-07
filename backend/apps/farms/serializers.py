from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from apps.accounts.models import FarmerProfile
from apps.accounts.roles import is_agrinuru_staff

from .models import Farm


class FarmSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and not request.user.is_superuser
            and not is_agrinuru_staff(request.user)
        ):
            self.fields["farmer"].queryset = FarmerProfile.objects.filter(user=request.user)
            self.fields["farmer"].required = False

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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:
            new_size = attrs.get(
                "approximate_size_acres",
                self.instance.approximate_size_acres,
            )
            allocated_size = self.instance.crops.aggregate(
                total=Sum("cultivated_area_acres")
            )["total"] or Decimal("0")
            if new_size < allocated_size:
                raise serializers.ValidationError({
                    "approximate_size_acres": (
                        f"This farm already has {allocated_size} acres allocated to crops. "
                        "Increase the farm size or reduce crop allocations before saving."
                    )
                })
        return attrs