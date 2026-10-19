from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    HarvestRecordViewSet,
    InputUsageViewSet,
    ProductionActivityViewSet,
    ProductionExpenseViewSet,
    ProductionSummaryView,
)

router = DefaultRouter()
router.register("activities", ProductionActivityViewSet, basename="production-activity")
router.register("inputs", InputUsageViewSet, basename="input-usage")
router.register("expenses", ProductionExpenseViewSet, basename="production-expense")
router.register("harvests", HarvestRecordViewSet, basename="harvest-record")

urlpatterns = [
    path("summary/", ProductionSummaryView.as_view(), name="production-summary"),
    path("", include(router.urls)),
]