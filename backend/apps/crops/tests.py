from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import FarmerProfile
from apps.accounts.roles import set_agrinuru_staff
from apps.crops.models import Crop
from apps.farms.models import Farm


def create_farm(size="10.00"):
    farmer = FarmerProfile.objects.create(
        full_name="Amina Wanjiku",
        phone_number="0712-345-678",
        email="amina@example.com",
        county="Nakuru",
        sub_county="Naivasha",
        preferred_language="Kiswahili",
    )
    return Farm.objects.create(
        farmer=farmer,
        farm_name="Green Valley",
        location="Naivasha",
        approximate_size_acres=size,
    )


def crop_data(farm_record, **overrides):
    return {
        "crop_name": "Maize",
        "variety": "H6213",
        "farm": farm_record.pk,
        "planting_date": "2026-03-01",
        "expected_harvest_date": "2026-08-01",
        "cultivated_area_acres": "2.50",
        "growth_stage": Crop.GrowthStage.PLANTED,
        "expected_harvest_quantity": "1200.00",
        "harvest_quantity_unit": Crop.QuantityUnit.KILOGRAM,
        **overrides,
    }


class CropModelTests(TestCase):
    def setUp(self):
        self.farm = create_farm()

    def test_crop_is_linked_to_farm_and_has_timestamps(self):
        crop = Crop.objects.create(
            farm=self.farm,
            crop_name="Maize",
            variety="H6213",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("2.50"),
            growth_stage=Crop.GrowthStage.PLANTED,
            expected_harvest_quantity=Decimal("1200.00"),
            harvest_quantity_unit=Crop.QuantityUnit.KILOGRAM,
        )

        self.assertEqual(crop.farm, self.farm)
        self.assertIn(crop, self.farm.crops.all())
        self.assertIsNotNone(crop.created_at)
        self.assertIsNotNone(crop.updated_at)

    def test_expected_harvest_date_cannot_precede_planting(self):
        crop = Crop(
            farm=self.farm,
            crop_name="Maize",
            planting_date="2026-08-01",
            expected_harvest_date="2026-03-01",
            cultivated_area_acres=Decimal("2.50"),
        )

        with self.assertRaises(ValidationError) as error:
            crop.full_clean()

        self.assertIn("expected_harvest_date", error.exception.message_dict)

    def test_area_cannot_exceed_farm_or_be_zero(self):
        for area in (Decimal("0"), Decimal("10.01")):
            crop = Crop(
                farm=self.farm,
                crop_name="Maize",
                planting_date="2026-03-01",
                expected_harvest_date="2026-08-01",
                cultivated_area_acres=area,
            )
            with self.subTest(area=area), self.assertRaises(ValidationError):
                crop.full_clean()

    def test_quantity_must_be_nonnegative_and_have_a_unit(self):
        crop = Crop(
            farm=self.farm,
            crop_name="Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("2.50"),
            expected_harvest_quantity=Decimal("-1"),
            harvest_quantity_unit=Crop.QuantityUnit.KILOGRAM,
        )

        with self.assertRaises(ValidationError) as error:
            crop.full_clean()

        self.assertIn("expected_harvest_quantity", error.exception.message_dict)

    def test_quantity_may_be_omitted_when_unit_is_omitted(self):
        crop = Crop(
            farm=self.farm,
            crop_name="Beans",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("1.00"),
        )

        crop.full_clean()


class CropApiTests(APITestCase):
    def setUp(self):
        self.farm = create_farm()
        user = get_user_model().objects.create_user(
            username="crop-api-user",
            email="crop-api-user@example.com",
            password="SecurePassword!98",
        )
        self.farm.farmer.user = user
        self.farm.farmer.save(update_fields=["user"])
        self.client.force_authenticate(user=user)

    def test_crop_crud_endpoints(self):
        create_response = self.client.post(
            reverse("crop-list"), crop_data(self.farm), format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        crop_id = create_response.data["id"]
        self.assertEqual(create_response.data["farm"], self.farm.pk)
        self.assertEqual(create_response.data["farm_name"], self.farm.farm_name)
        self.assertIn("created_at", create_response.data)
        self.assertIn("updated_at", create_response.data)

        list_response = self.client.get(reverse("crop-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        detail_url = reverse("crop-detail", args=[crop_id])
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        update_response = self.client.patch(
            detail_url, {"growth_stage": Crop.GrowthStage.FLOWERING}, format="json"
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["growth_stage"], Crop.GrowthStage.FLOWERING)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_crop_requires_existing_farm_and_required_fields(self):
        response = self.client.post(
            reverse("crop-list"),
            crop_data(self.farm, farm=99999, crop_name=""),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farm", response.data)
        self.assertIn("crop_name", response.data)

    def test_invalid_harvest_date_is_rejected(self):
        response = self.client.post(
            reverse("crop-list"),
            crop_data(
                self.farm,
                planting_date="2026-08-01",
                expected_harvest_date="2026-03-01",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expected_harvest_date", response.data)

    def test_area_over_farm_capacity_is_rejected(self):
        response = self.client.post(
            reverse("crop-list"),
            crop_data(self.farm, cultivated_area_acres="10.01"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cultivated_area_acres", response.data)

    def test_negative_quantity_and_missing_unit_are_rejected(self):
        negative_response = self.client.post(
            reverse("crop-list"),
            crop_data(self.farm, expected_harvest_quantity="-1"),
            format="json",
        )
        missing_unit_response = self.client.post(
            reverse("crop-list"),
            crop_data(self.farm, harvest_quantity_unit=""),
            format="json",
        )

        self.assertEqual(negative_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expected_harvest_quantity", negative_response.data)
        self.assertEqual(missing_unit_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("harvest_quantity_unit", missing_unit_response.data)

    def test_growth_stage_must_be_a_defined_choice(self):
        response = self.client.post(
            reverse("crop-list"),
            crop_data(self.farm, growth_stage="verified-by-ai"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("growth_stage", response.data)

    def test_quantity_can_be_omitted(self):
        payload = crop_data(
            self.farm,
            expected_harvest_quantity=None,
            harvest_quantity_unit="",
        )

        response = self.client.post(reverse("crop-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_farm_cannot_be_deleted_while_crops_exist(self):
        Crop.objects.create(
            farm=self.farm,
            crop_name="Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("2.50"),
        )

        response = self.client.delete(reverse("farm-detail", args=[self.farm.pk]))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("crop records", response.data["detail"])
        self.assertTrue(Farm.objects.filter(pk=self.farm.pk).exists())

    def test_farm_cannot_shrink_below_crop_allocations(self):
        Crop.objects.create(
            farm=self.farm,
            crop_name="Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("2.50"),
        )

        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"approximate_size_acres": "2.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already has 2.5 acres allocated", response.data["approximate_size_acres"][0])
        self.assertEqual(Farm.objects.get(pk=self.farm.pk).approximate_size_acres, Decimal("10.00"))
        self.assertEqual(Crop.objects.filter(farm=self.farm).count(), 1)

    def test_health_check_remains_available(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_farmer_can_only_list_retrieve_update_and_delete_own_crops(self):
        own_crop_response = self.client.post(
            reverse("crop-list"), crop_data(self.farm), format="json"
        )
        self.assertEqual(own_crop_response.status_code, status.HTTP_201_CREATED)
        other_farm = create_farm()
        other_crop = Crop.objects.create(
            farm=other_farm,
            crop_name="Other Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("1.00"),
        )

        listing = self.client.get(reverse("crop-list"))
        self.assertEqual([row["id"] for row in listing.data], [own_crop_response.data["id"]])
        self.assertEqual(
            self.client.get(reverse("crop-detail", args=[other_crop.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                reverse("crop-detail", args=[other_crop.pk]),
                {"growth_stage": Crop.GrowthStage.FLOWERING},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(reverse("crop-detail", args=[other_crop.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_farmer_cannot_create_or_move_crop_to_another_farm(self):
        other_farm = create_farm()
        create_foreign = self.client.post(
            reverse("crop-list"), crop_data(self.farm, farm=other_farm.pk), format="json"
        )
        self.assertEqual(create_foreign.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farm", create_foreign.data)

        own_crop = Crop.objects.create(
            farm=self.farm,
            crop_name="My Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("1.00"),
        )
        move_foreign = self.client.patch(
            reverse("crop-detail", args=[own_crop.pk]),
            {"farm": other_farm.pk},
            format="json",
        )
        self.assertEqual(move_foreign.status_code, status.HTTP_400_BAD_REQUEST)
        own_crop.refresh_from_db()
        self.assertEqual(own_crop.farm, self.farm)

    def test_staff_and_administrator_can_manage_crops_across_farmers(self):
        own_crop = Crop.objects.create(
            farm=self.farm,
            crop_name="First Farmer Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("1.00"),
        )
        other_farm = create_farm()
        other_crop = Crop.objects.create(
            farm=other_farm,
            crop_name="Staff Managed Maize",
            planting_date="2026-03-01",
            expected_harvest_date="2026-08-01",
            cultivated_area_acres=Decimal("1.00"),
        )
        staff_user = get_user_model().objects.create_user(
            username="crop-manager",
            email="crop-manager@example.com",
            password="SecurePassword!98",
        )
        set_agrinuru_staff(staff_user, True)
        self.client.force_authenticate(user=staff_user)

        staff_list = self.client.get(reverse("crop-list"))
        self.assertEqual({row["id"] for row in staff_list.data}, {own_crop.pk, other_crop.pk})
        staff_update = self.client.patch(
            reverse("crop-detail", args=[other_crop.pk]),
            {"growth_stage": Crop.GrowthStage.FLOWERING},
            format="json",
        )
        self.assertEqual(staff_update.status_code, status.HTTP_200_OK)

        administrator = get_user_model().objects.create_superuser(
            username="crop-administrator",
            email="crop-administrator@example.com",
            password="SecurePassword!98",
        )
        self.client.force_authenticate(user=administrator)
        admin_list = self.client.get(reverse("crop-list"))
        self.assertEqual({row["id"] for row in admin_list.data}, {own_crop.pk, other_crop.pk})