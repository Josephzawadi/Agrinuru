from rest_framework.routers import DefaultRouter

from .views import FarmerProfileViewSet

router = DefaultRouter()
router.register("farmers", FarmerProfileViewSet, basename="farmer")

urlpatterns = router.urls