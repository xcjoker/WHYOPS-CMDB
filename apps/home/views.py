from django.db.models import Count
from rest_framework.views import APIView
from apps.inform.models import Inform
from apps.inform.serializers import InformSerializer
from apps.idc.models import IdcRegion
from apps.idc.serializer import IdcRegionSerializer
from rest_framework.response import Response
from apps.oaauth.models import OADepartment
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator


class LatestInformView(APIView):
    # 返回最新的十条通知
    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        informs = Inform.objects.all().prefetch_related('reads')[:10]
        serializer = InformSerializer(informs, many=True)
        return Response(serializer.data)


class IDCView(APIView):
    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        idc = IdcRegion.objects.all()
        serializer = IdcRegionSerializer(idc, many=True)
        return Response(serializer.data)


class DepartmentStaffCountView(APIView):
    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        rows = OADepartment.objects.annotate(staff_count=Count('staffs')).values('name', 'staff_count')
        #print('='*10)
        return Response(rows)
