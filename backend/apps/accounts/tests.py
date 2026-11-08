from django.core.exceptions import ValidationError
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import FarmerProfile, validate_phone_number
from apps.accounts.roles import AGRINURU_STAFF_GROUP, set_agrinuru_staff
from apps.accounts.admin import AdministratorOnlyGroupAdmin, AdministratorOnlyUserAdmin
from apps.farms.models import Farm

User = get_user_model()


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
    def setUp(self):
        user = User.objects.create_user(
            username="existing-farmer-api",
            email="existing-farmer-api@example.com",
            password="SecurePassword!98",
        )
        set_agrinuru_staff(user, True)
        self.client.force_authenticate(user=user)

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

    def test_staff_can_manage_profiles_for_multiple_farmers(self):
        first_profile = FarmerProfile.objects.create(**farmer_data())
        second_profile = FarmerProfile.objects.create(
            **farmer_data(email="second-farmer@example.com")
        )

        listing = self.client.get(reverse("farmer-list"))
        self.assertEqual({row["id"] for row in listing.data}, {first_profile.pk, second_profile.pk})
        updated = self.client.patch(
            reverse("farmer-detail", args=[second_profile.pk]),
            {"county": "Kiambu"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

        administrator = User.objects.create_superuser(
            username="profile-administrator",
            email="profile-administrator@example.com",
            password="SecurePassword!98",
        )
        self.client.force_authenticate(user=administrator)
        admin_listing = self.client.get(reverse("farmer-list"))
        self.assertEqual(
            {row["id"] for row in admin_listing.data},
            {first_profile.pk, second_profile.pk},
        )


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        self.registration_data = {
            "username": "amina_farmer",
            "email": "amina@example.com",
            "full_name": "Amina Wanjiku",
            "phone_number": "+254 712 345 678",
            "county": "Nakuru",
            "sub_county": "Naivasha",
            "password": "SecurePassword!98",
        }

    def test_registration_creates_a_new_linked_profile_without_claiming_existing_profile(self):
        existing_profile = FarmerProfile.objects.create(**farmer_data())
        response = self.client.post(
            reverse("auth-register"),
            self.registration_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="amina_farmer")
        self.assertTrue(user.check_password(self.registration_data["password"]))
        self.assertNotEqual(user.password, self.registration_data["password"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.groups.count(), 0)
        self.assertEqual(response.data["role"], "farmer")
        self.assertTrue(response.data["has_farmer_profile"])
        self.assertEqual(FarmerProfile.objects.count(), 2)
        existing_profile.refresh_from_db()
        self.assertEqual(existing_profile.email, self.registration_data["email"])
        self.assertIsNone(existing_profile.user)
        registered_profile = FarmerProfile.objects.get(user=user)
        self.assertEqual(registered_profile.full_name, self.registration_data["full_name"])
        self.assertEqual(registered_profile.phone_number, self.registration_data["phone_number"])
        self.assertEqual(registered_profile.email, user.email)
        self.assertEqual(registered_profile.county, self.registration_data["county"])
        self.assertEqual(registered_profile.sub_county, self.registration_data["sub_county"])
        self.assertEqual(registered_profile.preferred_language, "English")
        self.assertEqual(
            set(response.data),
            {"id", "username", "email", "role", "has_farmer_profile"},
        )
        self.assertNotIn("password", response.data)
        self.client.force_authenticate(user=user)
        self.assertEqual(
            self.client.get(reverse("auth-current-user")).status_code,
            status.HTTP_200_OK,
        )
        farmer_listing = self.client.get(reverse("farmer-list"))
        self.assertEqual([row["id"] for row in farmer_listing.data], [registered_profile.pk])

    def test_registration_rejects_invalid_farmer_details_without_creating_account(self):
        response = self.client.post(
            reverse("auth-register"),
            {**self.registration_data, "phone_number": "not-a-phone"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)
        self.assertFalse(User.objects.filter(username=self.registration_data["username"]).exists())
        self.assertFalse(FarmerProfile.objects.exists())

    def test_registration_rejects_duplicate_username_and_email(self):
        self.client.post(
            reverse("auth-register"),
            self.registration_data,
            format="json",
        )

        duplicate_username = self.client.post(
            reverse("auth-register"),
            {
                **self.registration_data,
                "username": "AMINA_FARMER",
                "email": "another@example.com",
            },
            format="json",
        )
        duplicate_email = self.client.post(
            reverse("auth-register"),
            {
                **self.registration_data,
                "username": "another_farmer",
                "email": "AMINA@example.com",
            },
            format="json",
        )

        self.assertEqual(duplicate_username.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", duplicate_username.data)
        self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", duplicate_email.data)

    def test_registration_cannot_assign_privileged_flags(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                **self.registration_data,
                "is_staff": True,
                "is_superuser": True,
                "is_active": False,
                "role": "administrator",
                "groups": [AGRINURU_STAFF_GROUP],
                "permissions": ["auth.change_user"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="amina_farmer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.groups.exists())

    def test_login_establishes_session_and_invalid_credentials_are_generic(self):
        user = User.objects.create_user(
            username="amina_farmer",
            email="amina@example.com",
            password=self.registration_data["password"],
        )
        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": user.username,
                "password": self.registration_data["password"],
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("auth-current-user")).status_code, status.HTTP_200_OK)

        wrong_password = self.client.post(
            reverse("auth-login"),
            {"username": user.username, "password": "WrongPassword!98"},
            format="json",
        )
        unknown_user = self.client.post(
            reverse("auth-login"),
            {"username": "unknown", "password": "WrongPassword!98"},
            format="json",
        )
        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_password.data, unknown_user.data)

    def test_logout_ends_the_authenticated_session(self):
        User.objects.create_user(
            username="amina_farmer",
            email="amina@example.com",
            password=self.registration_data["password"],
        )
        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": "amina_farmer",
                "password": self.registration_data["password"],
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        logout_response = self.client.post(reverse("auth-logout"), format="json")

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(reverse("auth-current-user")).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_current_user_is_safe_and_requires_authentication(self):
        anonymous_response = self.client.get(reverse("auth-current-user"))
        self.assertEqual(anonymous_response.status_code, status.HTTP_403_FORBIDDEN)

        user = User.objects.create_user(
            username="amina_farmer",
            email="amina@example.com",
            password=self.registration_data["password"],
        )
        self.client.force_authenticate(user=user)
        authenticated_response = self.client.get(reverse("auth-current-user"))

        self.assertEqual(authenticated_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(authenticated_response.data),
            {"id", "username", "email", "role", "has_farmer_profile"},
        )
        self.assertEqual(authenticated_response.data["role"], "unlinked")
        self.assertFalse(authenticated_response.data["has_farmer_profile"])
        self.assertNotIn("password", authenticated_response.data)

    def test_linked_account_is_reported_as_farmer(self):
        user = User.objects.create_user(
            username="linked-farmer",
            email="linked@example.com",
            password=self.registration_data["password"],
        )
        FarmerProfile.objects.create(**farmer_data(), user=user)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("auth-current-user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "farmer")
        self.assertTrue(response.data["has_farmer_profile"])
        self.assertEqual(
            self.client.get(reverse("production-activity-list")).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(reverse("production-summary")).status_code,
            status.HTTP_200_OK,
        )

    def test_farmer_profile_access_is_limited_to_linked_profile(self):
        farmer_user = User.objects.create_user(
            username="profile-owner",
            email="profile-owner@example.com",
            password=self.registration_data["password"],
        )
        other_user = User.objects.create_user(
            username="other-profile-owner",
            email="other-profile-owner@example.com",
            password=self.registration_data["password"],
        )
        own_profile = FarmerProfile.objects.create(**farmer_data(), user=farmer_user)
        other_profile = FarmerProfile.objects.create(
            **farmer_data(email="other@example.com"),
            user=other_user,
        )
        self.client.force_authenticate(user=farmer_user)

        listed = self.client.get(reverse("farmer-list"))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in listed.data], [own_profile.pk])
        self.assertEqual(
            self.client.get(reverse("farmer-detail", args=[other_profile.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                reverse("farmer-detail", args=[other_profile.pk]),
                {"county": "Kiambu"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(reverse("farmer-detail", args=[other_profile.pk])).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                reverse("farmer-detail", args=[own_profile.pk]),
                {"user": other_user.pk},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        own_profile.refresh_from_db()
        self.assertEqual(own_profile.user, farmer_user)

        self.assertEqual(
            self.client.post(reverse("farmer-list"), farmer_data(), format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                reverse("farmer-link-account", args=[own_profile.pk]),
                {"user": None},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(reverse("farmer-detail", args=[own_profile.pk])).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_link_and_unlink_accounts_from_profiles(self):
        staff_user = User.objects.create_user(
            username="profile-link-staff",
            email="profile-link-staff@example.com",
            password=self.registration_data["password"],
        )
        set_agrinuru_staff(staff_user, True)
        target_user = User.objects.create_user(
            username="profile-link-target",
            email="profile-link-target@example.com",
            password=self.registration_data["password"],
        )
        profile = FarmerProfile.objects.create(**farmer_data())
        self.client.force_authenticate(user=staff_user)

        linked = self.client.post(
            reverse("farmer-link-account", args=[profile.pk]),
            {"user": target_user.pk},
            format="json",
        )
        self.assertEqual(linked.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.user, target_user)

        duplicate_profile = FarmerProfile.objects.create(
            **farmer_data(email="duplicate-profile@example.com")
        )
        duplicate_link = self.client.post(
            reverse("farmer-link-account", args=[duplicate_profile.pk]),
            {"user": target_user.pk},
            format="json",
        )
        self.assertEqual(duplicate_link.status_code, status.HTTP_400_BAD_REQUEST)

        unlinked = self.client.post(
            reverse("farmer-link-account", args=[profile.pk]),
            {"user": None},
            format="json",
        )
        self.assertEqual(unlinked.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertIsNone(profile.user)

    def test_unlinked_account_can_view_account_but_not_farmer_data(self):
        user = User.objects.create_user(
            username="unlinked-farmer",
            email="unlinked@example.com",
            password=self.registration_data["password"],
        )
        self.client.force_authenticate(user=user)

        account_response = self.client.get(reverse("auth-current-user"))
        self.assertEqual(account_response.status_code, status.HTTP_200_OK)
        self.assertEqual(account_response.data["role"], "unlinked")

        collection_routes = (
            "farmer-list",
            "farm-list",
            "crop-list",
            "production-activity-list",
            "input-usage-list",
            "production-expense-list",
            "harvest-record-list",
        )
        for route_name in (*collection_routes, "production-summary"):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        for route_name in collection_routes:
            with self.subTest(route_name=route_name, method="POST"):
                response = self.client.post(reverse(route_name), {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        detail_routes = (
            ("farmer-detail", "farmer-list"),
            ("farm-detail", "farm-list"),
            ("crop-detail", "crop-list"),
            ("production-activity-detail", "production-activity-list"),
            ("input-usage-detail", "input-usage-list"),
            ("production-expense-detail", "production-expense-list"),
            ("harvest-record-detail", "harvest-record-list"),
        )
        for detail_route, _ in detail_routes:
            detail_url = reverse(detail_route, args=[1])
            with self.subTest(route_name=detail_route, method="GET"):
                self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_403_FORBIDDEN)
            with self.subTest(route_name=detail_route, method="PATCH"):
                self.assertEqual(
                    self.client.patch(detail_url, {}, format="json").status_code,
                    status.HTTP_403_FORBIDDEN,
                )
            with self.subTest(route_name=detail_route, method="DELETE"):
                self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_403_FORBIDDEN)

        for void_route in (
            "production-activity-void",
            "input-usage-void",
            "production-expense-void",
            "harvest-record-void",
        ):
            with self.subTest(route_name=void_route, method="POST"):
                self.assertEqual(
                    self.client.post(
                        reverse(void_route, args=[1]), {"reason": "test"}, format="json"
                    ).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_is_staff_without_agrinuru_group_does_not_grant_data_access(self):
        user = User.objects.create_user(
            username="django-staff-only",
            email="django-staff@example.com",
            password=self.registration_data["password"],
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("farmer-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_administrator_can_assign_or_remove_staff_role(self):
        target = User.objects.create_user(
            username="staff-target",
            email="staff-target@example.com",
            password=self.registration_data["password"],
        )
        ordinary_user = User.objects.create_user(
            username="ordinary-user",
            email="ordinary@example.com",
            password=self.registration_data["password"],
        )
        self.client.force_authenticate(user=ordinary_user)

        denied = self.client.post(
            reverse("auth-staff-assignment", args=[ordinary_user.pk]),
            {"enabled": True},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        ordinary_user.refresh_from_db()
        self.assertFalse(ordinary_user.is_staff)
        self.assertFalse(ordinary_user.groups.exists())
        self.assertEqual(
            self.client.patch(
                reverse("auth-current-user"),
                {"role": "administrator"},
                format="json",
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        administrator = User.objects.create_superuser(
            username="administrator",
            email="administrator@example.com",
            password=self.registration_data["password"],
        )
        admin_client = APIClient()
        admin_client.force_authenticate(user=administrator)

        granted = admin_client.post(
            reverse("auth-staff-assignment", args=[target.pk]),
            {"enabled": True},
            format="json",
        )
        self.assertEqual(granted.status_code, status.HTTP_200_OK)
        self.assertEqual(granted.data["role"], "staff")
        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertTrue(target.groups.filter(name=AGRINURU_STAFF_GROUP).exists())

        revoked = admin_client.post(
            reverse("auth-staff-assignment", args=[target.pk]),
            {"enabled": False},
            format="json",
        )
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        self.assertEqual(revoked.data["role"], "unlinked")
        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertFalse(target.groups.filter(name=AGRINURU_STAFF_GROUP).exists())

    def test_administrator_retains_full_farmer_data_access(self):
        administrator = User.objects.create_superuser(
            username="full-administrator",
            email="full-admin@example.com",
            password=self.registration_data["password"],
        )
        self.client.force_authenticate(user=administrator)

        account_response = self.client.get(reverse("auth-current-user"))
        self.assertEqual(account_response.data["role"], "administrator")
        for route_name in (
            "farmer-list",
            "farm-list",
            "crop-list",
            "production-activity-list",
            "input-usage-list",
            "production-expense-list",
            "harvest-record-list",
            "production-summary",
        ):
            with self.subTest(route_name=route_name):
                self.assertEqual(
                    self.client.get(reverse(route_name)).status_code,
                    status.HTTP_200_OK,
                )

    def test_only_superusers_can_manage_users_and_groups_in_django_admin(self):
        staff_user = User.objects.create_user(
            username="staff-admin-surface",
            email="staff-admin@example.com",
            password=self.registration_data["password"],
            is_staff=True,
        )
        request = RequestFactory().get("/admin/")
        request.user = staff_user
        user_admin = AdministratorOnlyUserAdmin(User, admin.site)
        group_admin = AdministratorOnlyGroupAdmin(Group, admin.site)

        self.assertFalse(user_admin.has_module_permission(request))
        self.assertFalse(user_admin.has_add_permission(request))
        self.assertFalse(user_admin.has_change_permission(request))
        self.assertFalse(user_admin.has_delete_permission(request))
        self.assertFalse(group_admin.has_module_permission(request))
        self.assertFalse(group_admin.has_add_permission(request))
        self.assertFalse(group_admin.has_change_permission(request))
        self.assertFalse(group_admin.has_delete_permission(request))

        administrator = User.objects.create_superuser(
            username="django-admin-surface",
            email="django-admin-surface@example.com",
            password=self.registration_data["password"],
        )
        request.user = administrator
        self.assertTrue(user_admin.has_module_permission(request))
        self.assertTrue(user_admin.has_add_permission(request))
        self.assertTrue(user_admin.has_change_permission(request))
        self.assertTrue(user_admin.has_delete_permission(request))
        self.assertTrue(group_admin.has_module_permission(request))
        self.assertTrue(group_admin.has_add_permission(request))
        self.assertTrue(group_admin.has_change_permission(request))
        self.assertTrue(group_admin.has_delete_permission(request))

    def test_data_apis_require_authentication(self):
        for route_name in (
            "farmer-list",
            "farm-list",
            "crop-list",
            "production-activity-list",
            "input-usage-list",
            "production-expense-list",
            "harvest-record-list",
            "production-summary",
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_csrf_is_required_for_login_and_session_authenticated_writes(self):
        user = User.objects.create_user(
            username="amina_farmer",
            email="amina@example.com",
            password=self.registration_data["password"],
        )
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(reverse("auth-csrf"))
        csrf_token = csrf_response.data["csrfToken"]

        login_payload = {
            "username": user.username,
            "password": self.registration_data["password"],
        }
        rejected_login = client.post(
            reverse("auth-login"),
            login_payload,
            format="json",
        )
        self.assertEqual(rejected_login.status_code, status.HTTP_403_FORBIDDEN)

        accepted_login = client.post(
            reverse("auth-login"),
            login_payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted_login.status_code, status.HTTP_200_OK)

        rejected_write = client.post(
            reverse("farmer-list"),
            farmer_data(),
            format="json",
        )
        self.assertEqual(rejected_write.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse("auth-logout"), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)