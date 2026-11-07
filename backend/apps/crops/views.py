from rest_framework import viewsets

from apps.accounts.roles import is_agrinuru_staff

from .models import Crop
from .serializers import CropSerializer


class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.select_related("farm").all()
    serializer_class = CropSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser or is_agrinuru_staff(user):
            return queryset
        return queryset.filter(farm__farmer__user=user)