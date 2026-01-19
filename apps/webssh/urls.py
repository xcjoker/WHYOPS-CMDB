from django.urls import path
from .views import *

urlpatterns = [
    path('check', WebSSHView.as_view(), name='check')
]