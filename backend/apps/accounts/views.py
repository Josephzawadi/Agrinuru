from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FarmerProfile
from .permissions import IsAdministrator, IsStaffOrAdministrator
from .roles import is_agrinuru_staff, set_agrinuru_staff
from .serializers import (
    AccountSerializer,
    FarmerProfileAccountLinkSerializer,
    FarmerProfileSerializer,
    RegistrationSerializer,
    StaffAssignmentSerializer,
)

User = get_user_model()


class FarmerProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser or is_agrinuru_staff(user):
            return queryset
        return queryset.filter(user=user)

    def get_permissions(self):
        if self.action in {"create", "destroy", "link_account"}:
            return [IsAuthenticated(), IsStaffOrAdministrator()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        farmer = self.get_object()
        if farmer.farms.exists():
            return Response(
                {
                    "detail": (
                        "This farmer has registered farms and cannot be deleted. "
                        "Remove or reassign the farms first."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="link-account")
    def link_account(self, request, *args, **kwargs):
        farmer = self.get_object()
        serializer = FarmerProfileAccountLinkSerializer(
            farmer,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(FarmerProfileSerializer(farmer).data, status=status.HTTP_200_OK)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AccountSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)
        return Response(AccountSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Successfully logged out."})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data)


class StaffAssignmentView(APIView):
    permission_classes = [IsAdministrator]

    @transaction.atomic
    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        if target_user.is_superuser:
            return Response(
                {"detail": "Administrator accounts cannot be changed through staff assignment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StaffAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_agrinuru_staff(target_user, serializer.validated_data["enabled"])
        return Response(AccountSerializer(target_user).data, status=status.HTTP_200_OK)