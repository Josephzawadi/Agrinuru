from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import FarmerProfile
from apps.accounts.roles import set_agrinuru_staff
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
        user = get_user_model().objects.create_user(
            username="farm-api-user",
            email="farm-api-user@example.com",
            password="SecurePassword!98",
        )
        self.farmer.user = user
        self.farmer.save(update_fields=["user"])
        self.client.force_authenticate(user=user)

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

    def test_farmer_can_only_list_retrieve_update_and_delete_own_farms(self):
        own_farm = Farm.objects.create(
            farmer=self.farmer,
            farm_name="My Farm",
            location="Naivasha",
            approximate_size_acres="2.50",
        )
        other_farmer = create_farmer()
        other_farm = Farm.objects.create(
            farmer=other_farmer,
            farm_name="Other Farm",
            location="Nakuru",
            approximate_size_acres="3.00",
        )

        listing = self.client.get(reverse("farm-list"))
        self.assertEqual([row["id"] for row in listing.data], [own_farm.pk])
        self.assertEqual(
            self.client.get(reverse("farm-detail", args=[other_farm.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                reverse("farm-detail", args=[other_farm.pk]),
                {"farm_name": "Changed by another farmer"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(reverse("farm-detail", args=[other_farm.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_farmer_farm_creation_uses_own_profile_and_rejects_foreign_profile(self):
        other_farmer = create_farmer()
        payload = {
            "farm_name": "Automatically Owned Farm",
            "location": "Naivasha",
            "approximate_size_acres": "1.25",
        }

        created = self.client.post(reverse("farm-list"), payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["farmer"], self.farmer.pk)

        foreign = self.client.post(
            reverse("farm-list"),
            {**payload, "farmer": other_farmer.pk},
            format="json",
        )
        self.assertEqual(foreign.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farmer", foreign.data)

    def test_staff_and_administrator_can_manage_farms_across_farmers(self):
        own_farm = Farm.objects.create(
            farmer=self.farmer,
            farm_name="First Farmer Farm",
            location="Naivasha",
            approximate_size_acres="2.00",
        )
        other_farmer = create_farmer()
        other_farm = Farm.objects.create(
            farmer=other_farmer,
            farm_name="Other Farmer Farm",
            location="Nakuru",
            approximate_size_acres="3.00",
        )
        staff_user = get_user_model().objects.create_user(
            username="farm-manager",
            email="farm-manager@example.com",
            password="SecurePassword!98",
        )
        set_agrinuru_staff(staff_user, True)
        self.client.force_authenticate(user=staff_user)

        staff_list = self.client.get(reverse("farm-list"))
        self.assertEqual(
            {row["id"] for row in staff_list.data},
            {own_farm.pk, other_farm.pk},
        )
        staff_update = self.client.patch(
            reverse("farm-detail", args=[other_farm.pk]),
            {"farm_name": "Staff Updated Farm"},
            format="json",
        )
        self.assertEqual(staff_update.status_code, status.HTTP_200_OK)

        administrator = get_user_model().objects.create_superuser(
            username="farm-administrator",
            email="farm-administrator@example.com",
            password="SecurePassword!98",
        )
        self.client.force_authenticate(user=administrator)
        admin_list = self.client.get(reverse("farm-list"))
        self.assertEqual(
            {row["id"] for row in admin_list.data},
            {own_farm.pk, other_farm.pk},
        )