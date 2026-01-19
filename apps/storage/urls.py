from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'pvs', PVViewSet, basename='storage-pvs')
router.register(r'pvcs', PVCViewSet, basename='storage-pvcs')
router.register(r'storageclasses', StorageClassViewSet, basename='storage-storageclasses')

urlpatterns = router.urls
