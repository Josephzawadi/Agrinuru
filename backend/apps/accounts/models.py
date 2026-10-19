import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


def validate_phone_number(value):
    allowed_characters = re.fullmatch(r"\+?[0-9][0-9\s().-]*", value.strip())
    digit_count = sum(character.isdigit() for character in value)

    if not allowed_characters:
        raise ValidationError(
            "Use digits and common phone formatting characters only.",
            code="invalid_phone_characters",
        )
    if not 7 <= digit_count <= 15:
        raise ValidationError(
            "A phone number must contain between 7 and 15 digits.",
            code="invalid_phone_length",
        )


class FarmerProfile(models.Model):
    full_name = models.CharField(max_length=150, validators=[RegexValidator(r".*\S.*")])
    phone_number = models.CharField(max_length=30, validators=[validate_phone_number])
    email = models.EmailField(max_length=254)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100)
    preferred_language = models.CharField(max_length=50, default="English")
    date_registered = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["full_name", "id"]

    def __str__(self):
        return self.full_name