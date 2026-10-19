from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import FarmerProfile
from apps.farms.models import Farm


def create_farmer():
    return FarmerProfile.objects.create(
        full_name="Amina Wanjiku",
        phone_number="0712-345-678",
        email="amina@example.com",
        county="Nakuru",
        sub_county="Naivasha",
        preferred_language="Kiswahili",
    )


class FarmModelTests(TestCase):
    def setUp(self):
        self.farmer = create_farmer()

    def test_farm_is_related_to_its_farmer(self):
        farm = Farm.objects.create(
            farmer=self.farmer,
            farm_name="Green Valley",
            location="Naivasha",
            approximate_size_acres="2.50",
        )

        self.assertEqual(farm.farmer, self.farmer)
        self.assertIn(farm, self.farmer.farms.all())

    def test_farm_size_must_be_positive(self):
        farm = Farm(
            farmer=self.farmer,
            farm_name="Green Valley",
            location="Naivasha",
            approximate_size_acres="0",
        )

        with self.assertRaises(ValidationError) as error:
            farm.full_clean()

        self.assertIn("approximate_size_acres", error.exception.message_dict)

    def test_farmer_with_farms_is_protected_from_model_deletion(self):
        Farm.objects.create(
            farmer=self.farmer,
            farm_name="Green Valley",
            location="Naivasha",
            approximate_size_acres="2.50",
        )

        with self.assertRaises(ProtectedError):
            self.farmer.delete()


class FarmApiTests(APITestCase):
    def setUp(self):
        self.farmer = create_farmer()

    def test_farm_crud_endpoints(self):
        create_response = self.client.post(
            reverse("farm-list"),
            {
                "farmer": self.farmer.pk,
                "farm_name": "Green Valley",
                "location": "Naivasha",
                "approximate_size_acres": "2.50",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        farm_id = create_response.data["id"]
        self.assertEqual(create_response.data["farmer"], self.farmer.pk)
        self.assertIn("date_created", create_response.data)

        list_response = self.client.get(reverse("farm-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        detail_url = reverse("farm-detail", args=[farm_id])
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        update_response = self.client.patch(
            detail_url, {"farm_name": "Upper Green Valley"}, format="json"
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["farm_name"], "Upper Green Valley")

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_farm_requires_valid_farmer_and_positive_size(self):
        payload = {
            "farmer": 99999,
            "farm_name": "Green Valley",
            "location": "Naivasha",
            "approximate_size_acres": "-1",
        }

        response = self.client.post(reverse("farm-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farmer", response.data)
        self.assertIn("approximate_size_acres", response.data)