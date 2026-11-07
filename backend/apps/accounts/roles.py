from django.contrib.auth.models import Group

from .models import FarmerProfile

AGRINURU_STAFF_GROUP = "AgriNuru Staff"


class UserRole:
    ADMINISTRATOR = "administrator"
    STAFF = "staff"
    FARMER = "farmer"
    UNLINKED = "unlinked"


def has_farmer_profile(user):
    return bool(
        user.is_authenticated
        and FarmerProfile.objects.filter(user_id=user.pk).exists()
    )


def is_agrinuru_staff(user):
    return bool(
        user.is_authenticated
        and user.groups.filter(name=AGRINURU_STAFF_GROUP).exists()
    )


def get_user_role(user):
    if not user.is_authenticated:
        return UserRole.UNLINKED
    if user.is_superuser:
        return UserRole.ADMINISTRATOR
    if is_agrinuru_staff(user):
        return UserRole.STAFF
    if has_farmer_profile(user):
        return UserRole.FARMER
    return UserRole.UNLINKED


def set_agrinuru_staff(user, enabled):
    if user.is_superuser:
        raise ValueError("Administrator accounts cannot be changed through staff assignment.")

    group, _ = Group.objects.get_or_create(name=AGRINURU_STAFF_GROUP)
    if enabled:
        user.groups.add(group)
        return

    user.groups.remove(group)
