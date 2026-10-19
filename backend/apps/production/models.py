from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.crops.models import Crop


currency_code_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Enter a three-letter uppercase currency code, such as KES.",
)


class HistoricalProductionRecord(models.Model):
    crop = models.ForeignKey(
        Crop,
        on_delete=models.PROTECT,
        related_name="%(class)s_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True, default="")

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(voided_at__isnull=True, void_reason="")
                    | Q(voided_at__isnull=False) & ~Q(void_reason="")
                ),
                name="%(app_label)s_%(class)s_void_state_pair",
            ),
        ]

    @property
    def is_voided(self):
        return self.voided_at is not None

    def save(self, *args, **kwargs):
        if self.pk:
            previous_voided_at = type(self).objects.filter(pk=self.pk).values_list(
                "voided_at", flat=True
            ).first()
            if previous_voided_at is not None:
                raise ValidationError(
                    "Voided production records are immutable. Create a corrected replacement."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Production history cannot be deleted. Void the record with a reason instead."
        )

    def void(self, reason):
        if not self.pk:
            raise ValidationError({"detail": "Save the record before voiding it."})
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValidationError({"reason": "A reason is required to void this record."})
        if self.is_voided:
            raise ValidationError({"detail": "This record has already been voided."})
        self.voided_at = timezone.now()
        self.void_reason = cleaned_reason
        self.save(update_fields=["voided_at", "void_reason", "updated_at"])


class ProductionActivity(HistoricalProductionRecord):
    class ActivityType(models.TextChoices):
        PLANTING = "planting", "Planting"
        WEEDING = "weeding", "Weeding"
        IRRIGATION = "irrigation", "Irrigation"
        FERTILIZER_APPLICATION = "fertilizer_application", "Fertilizer application"
        PEST_CONTROL = "pest_control", "Pest control"
        PRUNING = "pruning", "Pruning"
        SOIL_PREPARATION = "soil_preparation", "Soil preparation"
        SCOUTING = "scouting", "Crop scouting"
        OTHER = "other", "Other"

    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    activity_date = models.DateField()
    description = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta(HistoricalProductionRecord.Meta):
        ordering = ["-activity_date", "id"]
        constraints = HistoricalProductionRecord.Meta.constraints + [
            models.CheckConstraint(
                condition=Q(
                    activity_type__in=(
                        "planting",
                        "weeding",
                        "irrigation",
                        "fertilizer_application",
                        "pest_control",
                        "pruning",
                        "soil_preparation",
                        "scouting",
                        "other",
                    )
                ),
                name="production_activity_type_valid",
            ),
        ]

    def clean(self):
        if self.activity_date and self.activity_date > timezone.localdate():
            raise ValidationError({"activity_date": "Completed activities cannot be future-dated."})


class InputUsage(HistoricalProductionRecord):
    class InputType(models.TextChoices):
        SEED = "seed", "Seed"
        FERTILIZER = "fertilizer", "Fertilizer"
        PESTICIDE = "pesticide", "Pesticide"
        HERBICIDE = "herbicide", "Herbicide"
        OTHER = "other", "Other"

    class QuantityUnit(models.TextChoices):
        GRAM = "g", "Grams"
        KILOGRAM = "kg", "Kilograms"
        TONNE = "tonne", "Tonnes"
        MILLILITRE = "ml", "Millilitres"
        LITRE = "l", "Litres"
        PIECE = "piece", "Pieces"
        PACKET = "packet", "Packets"
        BAG = "bag", "Bags"

    input_type = models.CharField(max_length=20, choices=InputType.choices)
    product_name = models.CharField(max_length=150)
    usage_date = models.DateField()
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantity_unit = models.CharField(max_length=10, choices=QuantityUnit.choices)
    purchase_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency_code = models.CharField(
        max_length=3,
        default="KES",
        validators=[currency_code_validator],
    )
    notes = models.TextField(blank=True)

    class Meta(HistoricalProductionRecord.Meta):
        ordering = ["-usage_date", "id"]
        constraints = HistoricalProductionRecord.Meta.constraints + [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="input_quantity_positive"),
            models.CheckConstraint(
                condition=Q(purchase_cost__isnull=True) | Q(purchase_cost__gte=0),
                name="input_purchase_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(
                    input_type__in=("seed", "fertilizer", "pesticide", "herbicide", "other")
                ),
                name="input_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    quantity_unit__in=(
                        "g",
                        "kg",
                        "tonne",
                        "ml",
                        "l",
                        "piece",
                        "packet",
                        "bag",
                    )
                ),
                name="input_quantity_unit_valid",
            ),
        ]

    def clean(self):
        if self.usage_date and self.usage_date > timezone.localdate():
            raise ValidationError({"usage_date": "Input usage cannot be future-dated."})


class ProductionExpense(HistoricalProductionRecord):
    class Category(models.TextChoices):
        LABOUR = "labour", "Labour"
        LAND_PREPARATION = "land_preparation", "Land preparation"
        IRRIGATION = "irrigation", "Irrigation"
        MACHINERY = "machinery", "Machinery"
        TRANSPORT = "transport", "Transport"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    category = models.CharField(max_length=24, choices=Category.choices)
    description = models.CharField(max_length=200)
    expense_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency_code = models.CharField(
        max_length=3,
        default="KES",
        validators=[currency_code_validator],
    )
    notes = models.TextField(blank=True)

    class Meta(HistoricalProductionRecord.Meta):
        ordering = ["-expense_date", "id"]
        constraints = HistoricalProductionRecord.Meta.constraints + [
            models.CheckConstraint(condition=Q(amount__gte=0), name="expense_amount_nonnegative"),
            models.CheckConstraint(
                condition=Q(
                    category__in=(
                        "labour",
                        "land_preparation",
                        "irrigation",
                        "machinery",
                        "transport",
                        "storage",
                        "other",
                    )
                ),
                name="production_expense_category_valid",
            ),
        ]

    def clean(self):
        if self.expense_date and self.expense_date > timezone.localdate():
            raise ValidationError({"expense_date": "Incurred expenses cannot be future-dated."})


class HarvestRecord(HistoricalProductionRecord):
    class QuantityUnit(models.TextChoices):
        KILOGRAM = "kg", "Kilograms"
        TONNE = "tonne", "Tonnes"

    harvest_date = models.DateField()
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    quantity_unit = models.CharField(max_length=10, choices=QuantityUnit.choices)
    notes = models.TextField(blank=True)

    class Meta(HistoricalProductionRecord.Meta):
        ordering = ["-harvest_date", "id"]
        constraints = HistoricalProductionRecord.Meta.constraints + [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="harvest_quantity_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_unit__in=("kg", "tonne")),
                name="harvest_quantity_unit_valid",
            ),
        ]

    def clean(self):
        errors = {}
        if self.harvest_date and self.harvest_date > timezone.localdate():
            errors["harvest_date"] = "Actual harvest dates cannot be in the future."
        if self.crop_id and self.harvest_date and self.harvest_date < self.crop.planting_date:
            errors["harvest_date"] = "Harvest date cannot precede the crop's planting date."
        if errors:
            raise ValidationError(errors)