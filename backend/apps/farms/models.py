from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from apps.accounts.models import FarmerProfile


class Farm(models.Model):
    farmer = models.ForeignKey(
        FarmerProfile,
        on_delete=models.PROTECT,
        related_name="farms",
    )
    farm_name = models.CharField(max_length=150, validators=[RegexValidator(r".*\S.*")])
    location = models.CharField(max_length=255, validators=[RegexValidator(r".*\S.*")])
    approximate_size_acres = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date_created = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["farm_name", "id"]

    def __str__(self):
        return self.farm_name