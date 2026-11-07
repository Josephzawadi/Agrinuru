from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.roles import UserRole, get_user_role
from apps.crops.models import Crop

from .models import HarvestRecord, InputUsage, ProductionActivity, ProductionExpense


class HistoricalRecordSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source="crop.crop_name", read_only=True)
    farm_id = serializers.IntegerField(source="crop.farm_id", read_only=True)
    farm_name = serializers.CharField(source="crop.farm.farm_name", read_only=True)
    farmer_id = serializers.IntegerField(source="crop.farm.farmer_id", read_only=True)
    farmer_name = serializers.CharField(
        source="crop.farm.farmer.full_name",
        read_only=True,
    )
    is_voided = serializers.BooleanField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and get_user_role(request.user) not in {
            UserRole.STAFF,
            UserRole.ADMINISTRATOR,
        }:
            self.fields["crop"].queryset = Crop.objects.filter(
                farm__farmer__user=request.user
            )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        record = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(record, field, value)

        try:
            record.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return attrs


class ProductionActivitySerializer(HistoricalRecordSerializer):
    class Meta:
        model = ProductionActivity
        fields = [
            "id",
            "crop",
            "crop_name",
            "farm_id",
            "farm_name",
            "farmer_id",
            "farmer_name",
            "activity_type",
            "activity_date",
            "description",
            "notes",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]


class InputUsageSerializer(HistoricalRecordSerializer):
    class Meta:
        model = InputUsage
        fields = [
            "id",
            "crop",
            "crop_name",
            "farm_id",
            "farm_name",
            "farmer_id",
            "farmer_name",
            "input_type",
            "product_name",
            "usage_date",
            "quantity",
            "quantity_unit",
            "purchase_cost",
            "currency_code",
            "notes",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]


class ProductionExpenseSerializer(HistoricalRecordSerializer):
    class Meta:
        model = ProductionExpense
        fields = [
            "id",
            "crop",
            "crop_name",
            "farm_id",
            "farm_name",
            "farmer_id",
            "farmer_name",
            "category",
            "description",
            "expense_date",
            "amount",
            "currency_code",
            "notes",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]


class HarvestRecordSerializer(HistoricalRecordSerializer):
    class Meta:
        model = HarvestRecord
        fields = [
            "id",
            "crop",
            "crop_name",
            "farm_id",
            "farm_name",
            "farmer_id",
            "farmer_name",
            "harvest_date",
            "quantity",
            "quantity_unit",
            "notes",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "voided_at",
            "void_reason",
            "is_voided",
        ]


class VoidRecordSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)