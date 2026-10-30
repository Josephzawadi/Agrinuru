from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group


class AdministratorOnlyAdminMixin:
    def has_module_permission(self, request):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)


class AdministratorOnlyUserAdmin(AdministratorOnlyAdminMixin, UserAdmin):
    pass


class AdministratorOnlyGroupAdmin(AdministratorOnlyAdminMixin, GroupAdmin):
    pass


User = get_user_model()
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, AdministratorOnlyUserAdmin)
admin.site.register(Group, AdministratorOnlyGroupAdmin)