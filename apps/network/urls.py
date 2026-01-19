from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'ingresses', IngressViewSet, basename='network-ingresses')

urlpatterns = router.urls
