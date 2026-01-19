from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'nodes', NodeViewSet, basename='node')
router.register(r'clusters', ClusterViewSet, basename='cluster')


urlpatterns = router.urls


