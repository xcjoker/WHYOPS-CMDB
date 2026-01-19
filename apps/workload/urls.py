from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'pods', PodViewSet, basename='pods')
router.register(r'deployments', DeploymentViewSet, basename='deployments')
router.register(r'statefulsets', StatefulSetViewSet, basename='statefulsets')
router.register(r'daemonsets', DaemonSetViewSet, basename='daemonsets')
router.register(r'jobs', JobViewSet, basename='jobs')
router.register(r'cronjobs', CronJobViewSet, basename='cronjobs')

urlpatterns = [
    path('', include(router.urls)),
]