from rest_framework import viewsets

from .models import Farm
from .serializers import FarmSerializer


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.select_related("farmer").all()
    serializer_class = FarmSerializer