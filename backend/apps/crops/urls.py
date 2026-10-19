from rest_framework.routers import DefaultRouter

from .views import CropViewSet

router = DefaultRouter()
router.register("crops", CropViewSet, basename="crop")

urlpatterns = router.urls