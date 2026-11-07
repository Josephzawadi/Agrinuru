from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Sum
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from apps.crops.models import Crop
from apps.accounts.permissions import HasFarmerDataAccess
from apps.accounts.roles import UserRole, get_user_role
from .models import HarvestRecord, InputUsage, ProductionActivity, ProductionExpense
from .serializers import (
    HarvestRecordSerializer,
    InputUsageSerializer,
    ProductionActivitySerializer,
    ProductionExpenseSerializer,
    VoidRecordSerializer,
)


def _parse_positive_id(value, name):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({name: "Enter a valid positive integer."}) from error
    if parsed < 1:
        raise ValidationError({name: "Enter a valid positive integer."})
    return parsed


def _parse_date_filter(value, name):
    if value is None:
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise ValidationError({name: "Use an ISO date in YYYY-MM-DD format."})
    return parsed


def _common_filters(query_params):
    filters = {}
    for parameter, field in (
        ("crop", "crop_id"),
        ("farm", "crop__farm_id"),
        ("farmer", "crop__farm__farmer_id"),
    ):
        value = query_params.get(parameter)
        if value is not None:
            filters[field] = _parse_positive_id(value, parameter)

    date_from = _parse_date_filter(query_params.get("date_from"), "date_from")
    date_to = _parse_date_filter(query_params.get("date_to"), "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError({"date_to": "End date cannot be before start date."})
    return filters, date_from, date_to


def _include_voided(query_params):
    value = query_params.get("include_voided", "false").lower()
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise ValidationError({"include_voided": "Use true or false."})


class ProductionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasFarmerDataAccess]
    date_field = None

    def get_queryset(self):
        queryset = self.queryset.select_related("crop", "crop__farm", "crop__farm__farmer")
        if get_user_role(self.request.user) not in {
            UserRole.STAFF,
            UserRole.ADMINISTRATOR,
        }:
            queryset = queryset.filter(crop__farm__farmer__user=self.request.user)

        filters, date_from, date_to = _common_filters(self.request.query_params)
        queryset = queryset.filter(**filters)
        if date_from:
            queryset = queryset.filter(**{f"{self.date_field}__gte": date_from})
        if date_to:
            queryset = queryset.filter(**{f"{self.date_field}__lte": date_to})

        include_voided = _include_voided(self.request.query_params)
        if not include_voided and self.action not in {"retrieve", "void", "destroy"}:
            queryset = queryset.filter(voided_at__isnull=True)
        return queryset

    def destroy(self, request, *args, **kwargs):
        record = self.get_object()
        return Response(
            {"detail": "Production history cannot be deleted. Void the record with a reason instead."},
            status=status.HTTP_409_CONFLICT,
        )

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, *args, **kwargs):
        record = self.get_object()
        serializer = VoidRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record.void(serializer.validated_data["reason"])
        except DjangoValidationError as error:
            details = error.message_dict if hasattr(error, "message_dict") else error.messages
            raise ValidationError(details) from error
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)


class ProductionActivityViewSet(ProductionRecordViewSet):
    queryset = ProductionActivity.objects.all()
    serializer_class = ProductionActivitySerializer
    date_field = "activity_date"


class InputUsageViewSet(ProductionRecordViewSet):
    queryset = InputUsage.objects.all()
    serializer_class = InputUsageSerializer
    date_field = "usage_date"


class ProductionExpenseViewSet(ProductionRecordViewSet):
    queryset = ProductionExpense.objects.all()
    serializer_class = ProductionExpenseSerializer
    date_field = "expense_date"


class HarvestRecordViewSet(ProductionRecordViewSet):
    queryset = HarvestRecord.objects.all()
    serializer_class = HarvestRecordSerializer
    date_field = "harvest_date"


def _quantity_in_kg(quantity, unit):
    if unit == Crop.QuantityUnit.KILOGRAM:
        return quantity
    if unit == Crop.QuantityUnit.TONNE:
        return quantity * Decimal("1000")
    return None


class ProductionSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasFarmerDataAccess]

    def get(self, request):
        crop_filters, date_from, date_to = _common_filters(request.query_params)
        crop_filter_fields = {
            "crop_id": "id",
            "crop__farm_id": "farm_id",
            "crop__farm__farmer_id": "farm__farmer_id",
        }
        crops = Crop.objects.select_related("farm", "farm__farmer").filter(
            **{crop_filter_fields[key]: value for key, value in crop_filters.items()}
        )
        if get_user_role(request.user) not in {
            UserRole.STAFF,
            UserRole.ADMINISTRATOR,
        }:
            crops = crops.filter(farm__farmer__user=request.user)

        crop_summaries = []
        cost_totals = defaultdict(lambda: {"input_purchases": Decimal("0"), "other_expenses": Decimal("0")})
        active_records = {"activities": 0, "input_usages": 0, "expenses": 0, "harvests": 0}

        for crop in crops:
            base_filter = {"crop": crop, "voided_at__isnull": True}
            activities = ProductionActivity.objects.filter(**base_filter)
            inputs = InputUsage.objects.filter(**base_filter)
            expenses = ProductionExpense.objects.filter(**base_filter)
            harvests = HarvestRecord.objects.filter(**base_filter)

            if date_from:
                activities = activities.filter(activity_date__gte=date_from)
                inputs = inputs.filter(usage_date__gte=date_from)
                expenses = expenses.filter(expense_date__gte=date_from)
                harvests = harvests.filter(harvest_date__gte=date_from)
            if date_to:
                activities = activities.filter(activity_date__lte=date_to)
                inputs = inputs.filter(usage_date__lte=date_to)
                expenses = expenses.filter(expense_date__lte=date_to)
                harvests = harvests.filter(harvest_date__lte=date_to)

            active_records["activities"] += activities.count()
            active_records["input_usages"] += inputs.count()
            active_records["expenses"] += expenses.count()
            active_records["harvests"] += harvests.count()

            harvest_rows = list(harvests.values("quantity", "quantity_unit"))
            actual_by_unit = defaultdict(lambda: Decimal("0"))
            actual_kg = Decimal("0")
            for row in harvest_rows:
                actual_by_unit[row["quantity_unit"]] += row["quantity"]
                actual_kg += _quantity_in_kg(row["quantity"], row["quantity_unit"])

            expected_quantity = crop.expected_harvest_quantity
            expected_unit = crop.harvest_quantity_unit
            expected_kg = (
                _quantity_in_kg(expected_quantity, expected_unit)
                if expected_quantity is not None
                else None
            )
            if expected_quantity is None or expected_kg is None:
                comparison_status = "expected_not_recorded_or_unit_incompatible"
            elif not harvest_rows:
                comparison_status = "no_harvest_recorded"
            elif date_from or date_to:
                comparison_status = "period_limited"
            else:
                comparison_status = "comparable"

            difference_kg = (
                actual_kg - expected_kg
                if comparison_status == "comparable"
                else None
            )

            input_cost_rows = inputs.exclude(purchase_cost__isnull=True).values(
                "currency_code"
            ).annotate(total=Sum("purchase_cost"))
            for row in input_cost_rows:
                cost_totals[row["currency_code"]]["input_purchases"] += row["total"] or Decimal("0")

            expense_rows = expenses.values("currency_code").annotate(total=Sum("amount"))
            for row in expense_rows:
                cost_totals[row["currency_code"]]["other_expenses"] += row["total"] or Decimal("0")

            input_usage_rows = inputs.values(
                "input_type", "product_name", "quantity_unit"
            ).annotate(quantity=Sum("quantity"))

            crop_summaries.append({
                "crop_id": crop.id,
                "crop_name": crop.crop_name,
                "variety": crop.variety,
                "farm_id": crop.farm_id,
                "farm_name": crop.farm.farm_name,
                "farmer_id": crop.farm.farmer_id,
                "farmer_name": crop.farm.farmer.full_name,
                "expected_harvest": {
                    "quantity": str(expected_quantity) if expected_quantity is not None else None,
                    "unit": expected_unit or None,
                    "normalized_kg": str(expected_kg) if expected_kg is not None else None,
                },
                "actual_harvest": {
                    "quantity_by_unit": {
                        unit: str(quantity) for unit, quantity in actual_by_unit.items()
                    },
                    "normalized_kg": str(actual_kg) if harvest_rows else None,
                    "record_count": len(harvest_rows),
                },
                "comparison": {
                    "status": comparison_status,
                    "unit": "kg" if comparison_status == "comparable" else None,
                    "difference_kg": str(difference_kg) if difference_kg is not None else None,
                },
                "input_usage_by_type_product_unit": list(input_usage_rows),
                "record_counts": {
                    "activities": activities.count(),
                    "input_usages": inputs.count(),
                    "expenses": expenses.count(),
                    "harvests": len(harvest_rows),
                },
            })

        cost_summary = []
        for currency, totals in sorted(cost_totals.items()):
            cost_summary.append({
                "currency_code": currency,
                "input_purchases": f"{totals['input_purchases']:.2f}",
                "other_expenses": f"{totals['other_expenses']:.2f}",
                "total": f"{totals['input_purchases'] + totals['other_expenses']:.2f}",
            })

        return Response({
            "filters": {
                "crop": crop_filters.get("crop_id"),
                "farm": crop_filters.get("crop__farm_id"),
                "farmer": crop_filters.get("crop__farm__farmer_id"),
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            "harvest_comparison_scope": "selected_period_only" if date_from or date_to else "full_recorded_season",
            "crops": crop_summaries,
            "active_record_counts": active_records,
            "costs_by_currency": cost_summary,
        })