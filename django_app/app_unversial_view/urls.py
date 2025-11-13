from rest_framework.routers import DefaultRouter
from .cuoponView import UniversalCouponViewSet

router = DefaultRouter()
router.register('coupon-generate', UniversalCouponViewSet, basename='coupon')

urlpatterns = router.urls