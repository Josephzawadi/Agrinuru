from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import FarmerProfile
from .serializers import FarmerProfileSerializer


class FarmerProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerProfileSerializer

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