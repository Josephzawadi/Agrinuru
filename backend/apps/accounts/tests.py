from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import FarmerProfile, validate_phone_number
from apps.farms.models import Farm


def farmer_data(**overrides):
    return {
        "full_name": "Amina Wanjiku",
        "phone_number": "+254 712 345 678",
        "email": "amina@example.com",
        "county": "Nakuru",
        "sub_county": "Naivasha",
        "preferred_language": "Kiswahili",
        **overrides,
    }


class FarmerProfileModelTests(TestCase):
    def test_valid_kenyan_phone_formats_are_accepted(self):
        validate_phone_number("+254 712 345 678")
        validate_phone_number("0712-345-678")

    def test_phone_with_letters_is_rejected(self):
        farmer = FarmerProfile(**farmer_data(phone_number="0712ABC345"))

        with self.assertRaises(ValidationError):
            farmer.full_clean()

    def test_required_fields_and_email_are_validated(self):
        farmer = FarmerProfile(**farmer_data(full_name="", email="not-an-email"))

        with self.assertRaises(ValidationError) as error:
            farmer.full_clean()

        self.assertIn("full_name", error.exception.message_dict)
        self.assertIn("email", error.exception.message_dict)


class FarmerApiTests(APITestCase):
    def test_farmer_crud_endpoints(self):
        create_response = self.client.post(
            reverse("farmer-list"), farmer_data(), format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        farmer_id = create_response.data["id"]
        self.assertIn("date_registered", create_response.data)

        list_response = self.client.get(reverse("farmer-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        detail_url = reverse("farmer-detail", args=[farmer_id])
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        update_response = self.client.patch(
            detail_url, {"county": "Kiambu"}, format="json"
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["county"], "Kiambu")

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FarmerProfile.objects.filter(pk=farmer_id).exists())

    def test_invalid_farmer_fields_return_validation_errors(self):
        response = self.client.post(
            reverse("farmer-list"),
            farmer_data(full_name="", email="invalid", phone_number="call me"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data)
        self.assertIn("email", response.data)
        self.assertIn("phone_number", response.data)

    def test_required_farmer_fields_cannot_be_omitted(self):
        response = self.client.post(reverse("farmer-list"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in (
            "full_name",
            "phone_number",
            "email",
            "county",
            "sub_county",
            "preferred_language",
        ):
            self.assertIn(field, response.data)

    def test_farmer_with_farms_cannot_be_deleted(self):
        farmer = FarmerProfile.objects.create(**farmer_data())
        Farm.objects.create(
            farmer=farmer,
            farm_name="Green Valley",
            location="Naivasha",
            approximate_size_acres="2.50",
        )

        response = self.client.delete(reverse("farmer-detail", args=[farmer.pk]))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["detail"],
            "This farmer has registered farms and cannot be deleted. "
            "Remove or reassign the farms first.",
        )
        self.assertTrue(FarmerProfile.objects.filter(pk=farmer.pk).exists())