from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CsrfTokenView,
    CurrentUserView,
    FarmerProfileViewSet,
    LoginView,
    LogoutView,
    RegistrationView,
    StaffAssignmentView,
)

router = DefaultRouter()
router.register("farmers", FarmerProfileViewSet, basename="farmer")

urlpatterns = [
    path("auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/register/", RegistrationView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-current-user"),
    path("auth/staff/<int:user_id>/", StaffAssignmentView.as_view(), name="auth-staff-assignment"),
] + router.urls