from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

urlpatterns = [
    path('server/', IdcServerView.as_view(), name='server'),
    path('server/<int:pk>/', IdcServerView.as_view(), name='server_delete'),
    path('server/api/', IdcServerAPIView.as_view(), name='serverApi'),
    path('server/update/<int:pk>/', IdcServerUpdateView.as_view()),
    path('server/monitor/', IdcServerMonitor.as_view(), name='monitor')
]
router = DefaultRouter()
router.register('region', IdcRegionView, basename='region')
urlpatterns += router.urls
