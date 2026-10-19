from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from apps.farms.models import Farm


class Crop(models.Model):
    class GrowthStage(models.TextChoices):
        PLANNED = "planned", "Planned"
        PLANTED = "planted", "Planted"
        GERMINATING = "germinating", "Germinating"
        VEGETATIVE = "vegetative", "Vegetative"
        FLOWERING = "flowering", "Flowering"
        FRUITING = "fruiting", "Fruiting"
        MATURING = "maturing", "Maturing"
        HARVESTED = "harvested", "Harvested"

    class QuantityUnit(models.TextChoices):
        KILOGRAM = "kg", "Kilograms"
        TONNE = "tonne", "Tonnes"

    farm = models.ForeignKey(
        Farm,
        on_delete=models.PROTECT,
        related_name="crops",
    )
    crop_name = models.CharField(
        max_length=120,
        validators=[RegexValidator(r".*\S.*")],
    )
    variety = models.CharField(max_length=120, blank=True)
    planting_date = models.DateField()
    expected_harvest_date = models.DateField()
    cultivated_area_acres = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    growth_stage = models.CharField(
        max_length=20,
        choices=GrowthStage.choices,
        default=GrowthStage.PLANNED,
    )
    expected_harvest_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    harvest_quantity_unit = models.CharField(
        max_length=10,
        choices=QuantityUnit.choices,
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-planting_date", "crop_name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cultivated_area_acres__gt=0),
                name="crop_area_positive",
            ),
            models.CheckConstraint(
                condition=Q(expected_harvest_quantity__isnull=True)
                | Q(expected_harvest_quantity__gte=0),
                name="crop_quantity_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(expected_harvest_date__gte=models.F("planting_date")),
                name="crop_harvest_not_before_planting",
            ),
            models.CheckConstraint(
                condition=(
                    Q(expected_harvest_quantity__isnull=True, harvest_quantity_unit="")
                    | Q(
                        expected_harvest_quantity__isnull=False,
                        harvest_quantity_unit__in=("kg", "tonne"),
                    )
                ),
                name="crop_quantity_unit_pair",
            ),
        ]

    def clean(self):
        errors = {}

        if self.planting_date and self.expected_harvest_date:
            if self.expected_harvest_date < self.planting_date:
                errors["expected_harvest_date"] = (
                    "Expected harvest date cannot be before the planting date."
                )

        if self.expected_harvest_quantity is None and self.harvest_quantity_unit:
            errors["harvest_quantity_unit"] = (
                "Provide an expected harvest quantity when selecting a unit."
            )
        elif self.expected_harvest_quantity is not None and not self.harvest_quantity_unit:
            errors["harvest_quantity_unit"] = (
                "Select a unit when an expected harvest quantity is provided."
            )

        if self.farm_id and self.cultivated_area_acres is not None:
            farm = self.farm
            other_crops = Crop.objects.filter(farm_id=self.farm_id).exclude(pk=self.pk)
            already_allocated = other_crops.aggregate(total=Sum("cultivated_area_acres"))["total"]
            total_area = (already_allocated or Decimal("0")) + self.cultivated_area_acres
            farm_size = Decimal(str(farm.approximate_size_acres))
            if total_area > farm_size:
                errors["cultivated_area_acres"] = (
                    f"This crop would allocate {total_area} acres, exceeding the "
                    f"farm's {farm_size} registered acres."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.crop_name} - {self.farm.farm_name}"