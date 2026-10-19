from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Farm
from .serializers import FarmSerializer


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.select_related("farmer").all()
    serializer_class = FarmSerializer

    def destroy(self, request, *args, **kwargs):
        farm = self.get_object()
        if farm.crops.exists():
            return Response(
                {"detail": "This farm has crop records and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This farm has crop records and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )