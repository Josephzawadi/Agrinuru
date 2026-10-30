from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import FarmerProfile
from apps.crops.models import Crop
from apps.farms.models import Farm
from apps.production.models import (
    HarvestRecord,
    InputUsage,
    ProductionActivity,
    ProductionExpense,
)


def create_farm_and_crop(
    *,
    email="amina@example.com",
    expected_quantity=Decimal("1000.00"),
    expected_unit=Crop.QuantityUnit.KILOGRAM,
):
    farmer = FarmerProfile.objects.create(
        full_name="Amina Wanjiku",
        phone_number="0712-345-678",
        email=email,
        county="Nakuru",
        sub_county="Naivasha",
        preferred_language="Kiswahili",
    )
    farm = Farm.objects.create(
        farmer=farmer,
        farm_name=f"Farm {email}",
        location="Naivasha",
        approximate_size_acres=Decimal("20.00"),
    )
    crop = Crop.objects.create(
        farm=farm,
        crop_name="Maize",
        variety="H6213",
        planting_date="2026-03-01",
        expected_harvest_date="2026-08-01",
        cultivated_area_acres=Decimal("5.00"),
        growth_stage=Crop.GrowthStage.PLANTED,
        expected_harvest_quantity=expected_quantity,
        harvest_quantity_unit=expected_unit,
    )
    crop.refresh_from_db()
    return farmer, farm, crop


def activity_data(crop, **overrides):
    return {
        "crop": crop.pk,
        "activity_type": ProductionActivity.ActivityType.WEEDING,
        "activity_date": "2026-02-20",
        "description": "First field weeding",
        "notes": "Completed by hand",
        **overrides,
    }


def input_data(crop, **overrides):
    return {
        "crop": crop.pk,
        "input_type": InputUsage.InputType.FERTILIZER,
        "product_name": "NPK 17:17:17",
        "usage_date": "2026-02-25",
        "quantity": "25.000",
        "quantity_unit": InputUsage.QuantityUnit.KILOGRAM,
        "purchase_cost": "1800.00",
        "currency_code": "KES",
        "notes": "Applied before planting",
        **overrides,
    }


def expense_data(crop, **overrides):
    return {
        "crop": crop.pk,
        "category": ProductionExpense.Category.LABOUR,
        "description": "Land preparation workers",
        "expense_date": "2026-02-15",
        "amount": "2500.00",
        "currency_code": "KES",
        "notes": "",
        **overrides,
    }


def harvest_data(crop_record, **overrides):
    return {
        "crop": crop_record.pk,
        "harvest_date": "2026-08-10",
        "quantity": "500.000",
        "quantity_unit": HarvestRecord.QuantityUnit.KILOGRAM,
        "notes": "First picking",
        **overrides,
    }


def model_data(data, crop):
    values = {**data, "crop": crop}
    for field in ("activity_date", "usage_date", "expense_date", "harvest_date"):
        if field in values and isinstance(values[field], str):
            values[field] = date.fromisoformat(values[field])
    return values


class ProductionModelTests(TestCase):
    def setUp(self):
        self.farmer, self.farm, self.crop = create_farm_and_crop()

    def test_activity_and_expense_can_precede_planting(self):
        activity = ProductionActivity(**model_data(activity_data(self.crop), self.crop))
        expense = ProductionExpense(**model_data(expense_data(self.crop), self.crop))

        activity.full_clean()
        expense.full_clean()

    def test_input_quantity_must_be_positive_and_cost_nonnegative(self):
        invalid_input = InputUsage(
            **model_data(input_data(self.crop, quantity="0"), self.crop)
        )
        with self.assertRaises(ValidationError):
            invalid_input.full_clean()

        invalid_cost = InputUsage(
            **model_data(input_data(self.crop, purchase_cost="-1"), self.crop)
        )
        with self.assertRaises(ValidationError):
            invalid_cost.full_clean()

    def test_currency_code_must_be_three_uppercase_letters(self):
        invalid_expense = ProductionExpense(
            **model_data(expense_data(self.crop, currency_code="kes"), self.crop)
        )

        with self.assertRaises(ValidationError) as error:
            invalid_expense.full_clean()

        self.assertIn("currency_code", error.exception.message_dict)

    def test_harvest_allows_zero_and_rejects_negative(self):
        zero_harvest = HarvestRecord(
            **model_data(harvest_data(self.crop, quantity="0"), self.crop)
        )
        zero_harvest.full_clean()

        negative_harvest = HarvestRecord(
            **model_data(harvest_data(self.crop, quantity="-1"), self.crop)
        )
        with self.assertRaises(ValidationError):
            negative_harvest.full_clean()

    def test_harvest_cannot_precede_crop_planting(self):
        harvest = HarvestRecord(
            **model_data(harvest_data(self.crop, harvest_date="2026-02-28"), self.crop)
        )

        with self.assertRaises(ValidationError) as error:
            harvest.full_clean()

        self.assertIn("harvest_date", error.exception.message_dict)

    def test_void_requires_reason_and_makes_record_immutable(self):
        activity = ProductionActivity.objects.create(
            **model_data(activity_data(self.crop), self.crop)
        )
        with self.assertRaises(ValidationError):
            activity.void("   ")

        activity.void("Corrected entry")
        self.assertTrue(activity.is_voided)
        self.assertEqual(activity.void_reason, "Corrected entry")
        with self.assertRaises(ValidationError):
            activity.description = "Edited after void"
            activity.save()
        with self.assertRaises(ValidationError):
            activity.delete()


class ProductionApiTests(APITestCase):
    def setUp(self):
        self.farmer, self.farm, self.crop = create_farm_and_crop()
        user = get_user_model().objects.create_user(
            username="production-api-user",
            email="production-api-user@example.com",
            password="SecurePassword!98",
        )
        self.farmer.user = user
        self.farmer.save(update_fields=["user"])
        self.client.force_authenticate(user=user)

    def test_create_activity_and_filter_by_crop_farm_farmer_and_date(self):
        response = self.client.post(
            reverse("production-activity-list"), activity_data(self.crop), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["crop_name"], self.crop.crop_name)
        self.assertEqual(response.data["farm_id"], self.farm.pk)
        self.assertEqual(response.data["farmer_id"], self.farmer.pk)

        for query in (
            f"?crop={self.crop.pk}",
            f"?farm={self.farm.pk}",
            f"?farmer={self.farmer.pk}",
            "?date_from=2026-02-01&date_to=2026-02-28",
        ):
            with self.subTest(query=query):
                filtered = self.client.get(reverse("production-activity-list") + query)
                self.assertEqual(filtered.status_code, status.HTTP_200_OK)
                self.assertEqual(len(filtered.data), 1)

    def test_activity_crud_and_completed_date_validation(self):
        created = self.client.post(
            reverse("production-activity-list"), activity_data(self.crop), format="json"
        )
        detail_url = reverse("production-activity-detail", args=[created.data["id"]])
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        update = self.client.patch(detail_url, {"notes": "Checked"}, format="json")
        self.assertEqual(update.status_code, status.HTTP_200_OK)

        void_response = self.client.post(
            reverse("production-activity-void", args=[created.data["id"]]),
            {"reason": "Entered against the wrong crop"},
            format="json",
        )
        self.assertEqual(void_response.status_code, status.HTTP_200_OK)

        hard_delete = self.client.delete(detail_url)
        self.assertEqual(hard_delete.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(
            ProductionActivity.objects.filter(pk=created.data["id"], voided_at__isnull=False).exists()
        )

        future_response = self.client.post(
            reverse("production-activity-list"),
            activity_data(self.crop, activity_date="2099-01-01"),
            format="json",
        )
        self.assertEqual(future_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activity_date", future_response.data)

    def test_void_requires_reason_and_is_excluded_from_default_lists(self):
        created = self.client.post(
            reverse("production-expense-list"), expense_data(self.crop), format="json"
        )
        void_url = reverse("production-expense-void", args=[created.data["id"]])
        missing_reason = self.client.post(void_url, {"reason": "  "}, format="json")
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)

        voided = self.client.post(void_url, {"reason": "Duplicate entry"}, format="json")
        self.assertEqual(voided.status_code, status.HTTP_200_OK)
        self.assertEqual(voided.data["void_reason"], "Duplicate entry")
        self.assertEqual(len(self.client.get(reverse("production-expense-list")).data), 0)
        self.assertEqual(
            len(self.client.get(reverse("production-expense-list") + "?include_voided=true").data),
            1,
        )

    def test_input_crud_validation_and_default_currency(self):
        response = self.client.post(
            reverse("input-usage-list"),
            input_data(self.crop, purchase_cost=None),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["currency_code"], "KES")

        detail_url = reverse("input-usage-detail", args=[response.data["id"]])
        updated = self.client.patch(detail_url, {"notes": "Applied"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

        zero_quantity = self.client.post(
            reverse("input-usage-list"), input_data(self.crop, quantity="0"), format="json"
        )
        self.assertEqual(zero_quantity.status_code, status.HTTP_400_BAD_REQUEST)

        bad_currency = self.client.post(
            reverse("input-usage-list"), input_data(self.crop, currency_code="KES1"), format="json"
        )
        self.assertEqual(bad_currency.status_code, status.HTTP_400_BAD_REQUEST)

        bad_unit = self.client.post(
            reverse("input-usage-list"),
            input_data(self.crop, quantity_unit="bucket"),
            format="json",
        )
        self.assertEqual(bad_unit.status_code, status.HTTP_400_BAD_REQUEST)

        default_currency_payload = input_data(self.crop)
        default_currency_payload.pop("currency_code")
        default_currency = self.client.post(
            reverse("input-usage-list"), default_currency_payload, format="json"
        )
        self.assertEqual(default_currency.status_code, status.HTTP_201_CREATED)
        self.assertEqual(default_currency.data["currency_code"], "KES")

        future_usage = self.client.post(
            reverse("input-usage-list"), input_data(self.crop, usage_date="2099-01-01"), format="json"
        )
        self.assertEqual(future_usage.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expense_crud_and_negative_amount_validation(self):
        response = self.client.post(
            reverse("production-expense-list"), expense_data(self.crop), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["currency_code"], "KES")

        updated = self.client.patch(
            reverse("production-expense-detail", args=[response.data["id"]]),
            {"description": "Updated labour cost"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

        negative = self.client.post(
            reverse("production-expense-list"), expense_data(self.crop, amount="-1"), format="json"
        )
        self.assertEqual(negative.status_code, status.HTTP_400_BAD_REQUEST)

    def test_harvest_crud_zero_quantity_and_invalid_dates(self):
        response = self.client.post(
            reverse("harvest-record-list"), harvest_data(self.crop, quantity="0"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        updated = self.client.patch(
            reverse("harvest-record-detail", args=[response.data["id"]]),
            {"notes": "Zero yield recorded"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

        negative = self.client.post(
            reverse("harvest-record-list"), harvest_data(self.crop, quantity="-1"), format="json"
        )
        self.assertEqual(negative.status_code, status.HTTP_400_BAD_REQUEST)

        before_planting = self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, harvest_date="2026-02-28"),
            format="json",
        )
        self.assertEqual(before_planting.status_code, status.HTTP_400_BAD_REQUEST)

        bad_unit = self.client.post(
            reverse("harvest-record-list"), harvest_data(self.crop, quantity_unit="bag"), format="json"
        )
        self.assertEqual(bad_unit.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_crop_reference_and_date_filters_are_rejected(self):
        invalid_crop = self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, crop=99999),
            format="json",
        )
        self.assertEqual(invalid_crop.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_date = self.client.get(reverse("harvest-record-list") + "?date_from=not-a-date")
        self.assertEqual(invalid_date.status_code, status.HTTP_400_BAD_REQUEST)

        reversed_range = self.client.get(
            reverse("harvest-record-list") + "?date_from=2026-09-01&date_to=2026-08-01"
        )
        self.assertEqual(reversed_range.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_normalizes_harvest_units_and_groups_costs_by_currency(self):
        self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, quantity="0.500", quantity_unit="tonne"),
            format="json",
        )
        self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, quantity="200.000", quantity_unit="kg"),
            format="json",
        )
        self.client.post(
            reverse("input-usage-list"), input_data(self.crop, purchase_cost="200.00"), format="json"
        )
        self.client.post(
            reverse("input-usage-list"), input_data(self.crop, purchase_cost="10.00", currency_code="USD"), format="json"
        )
        self.client.post(
            reverse("production-expense-list"), expense_data(self.crop, amount="300.00"), format="json"
        )

        response = self.client.get(reverse("production-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        crop_summary = response.data["crops"][0]
        self.assertEqual(crop_summary["actual_harvest"]["normalized_kg"], "700.000")
        self.assertEqual(crop_summary["expected_harvest"]["normalized_kg"], "1000.00")
        self.assertEqual(crop_summary["comparison"]["status"], "comparable")
        self.assertEqual(crop_summary["comparison"]["difference_kg"], "-300.000")
        cost_by_currency = {row["currency_code"]: row for row in response.data["costs_by_currency"]}
        self.assertEqual(cost_by_currency["KES"]["total"], "500.00")
        self.assertEqual(cost_by_currency["USD"]["total"], "10.00")

    def test_summary_does_not_treat_missing_expectation_as_zero(self):
        Crop.objects.filter(pk=self.crop.pk).update(
            expected_harvest_quantity=None,
            harvest_quantity_unit="",
        )
        self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, quantity="250.000"),
            format="json",
        )

        response = self.client.get(reverse("production-summary"))

        comparison = response.data["crops"][0]["comparison"]
        self.assertEqual(comparison["status"], "expected_not_recorded_or_unit_incompatible")
        self.assertIsNone(comparison["difference_kg"])

    def test_date_filtered_summary_is_period_limited_and_excludes_voided_harvest(self):
        first = self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, harvest_date="2026-07-01", quantity="100.000"),
            format="json",
        )
        second = self.client.post(
            reverse("harvest-record-list"),
            harvest_data(self.crop, harvest_date="2026-08-10", quantity="200.000"),
            format="json",
        )
        self.client.post(
            reverse("harvest-record-void", args=[second.data["id"]]),
            {"reason": "Duplicate harvest entry"},
            format="json",
        )

        response = self.client.get(
            reverse("production-summary") + "?date_from=2026-06-01&date_to=2026-07-31"
        )

        crop_summary = response.data["crops"][0]
        self.assertEqual(crop_summary["actual_harvest"]["normalized_kg"], "100.000")
        self.assertEqual(crop_summary["comparison"]["status"], "period_limited")
        self.assertIsNone(crop_summary["comparison"]["difference_kg"])
        self.assertEqual(crop_summary["record_counts"]["harvests"], 1)
        self.assertTrue(HarvestRecord.objects.filter(pk=first.data["id"]).exists())

    def test_summary_filters_by_farm_and_farmer(self):
        _, other_farm, _ = create_farm_and_crop(email="other@example.com")
        summary_by_farm = self.client.get(
            reverse("production-summary") + f"?farm={self.farm.pk}"
        )
        summary_by_crop = self.client.get(
            reverse("production-summary") + f"?crop={self.crop.pk}"
        )
        summary_by_farmer = self.client.get(
            reverse("production-summary") + f"?farmer={self.farmer.pk}"
        )
        summary_other_farm = self.client.get(
            reverse("production-summary") + f"?farm={other_farm.pk}"
        )

        self.assertEqual(len(summary_by_farm.data["crops"]), 1)
        self.assertEqual(len(summary_by_crop.data["crops"]), 1)
        self.assertEqual(len(summary_by_farmer.data["crops"]), 1)
        self.assertEqual(len(summary_other_farm.data["crops"]), 1)
        self.assertEqual(summary_by_crop.data["filters"]["crop"], self.crop.pk)

    def test_health_check_remains_available(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")