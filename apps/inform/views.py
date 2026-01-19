from django.db.models import Prefetch
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView

from .models import Inform, InformRead
from .serializers import InformSerializer, ReadInformSerializer
from rest_framework.response import Response
from rest_framework import status


# Create your views here.
class InformViewSet(viewsets.ModelViewSet):
    queryset = Inform.objects.all()
    serializer_class = InformSerializer

    # 给字段reads过滤
    def get_queryset(self):
        queryset = self.queryset.prefetch_related(
            Prefetch("reads", queryset=InformRead.objects.filter(user_id=self.request.user.uid))
        )

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author.uid == request.user.uid:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    # 如何区分调用的是list还是retrieve DjangoRESTFramework根据路由的配置自动区分：如果URL不包含主键（ / resource /），则调用list()。如果URL
    # 包含主键（ / resource / < pk > / ），则调用retrieve()。
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        data['read_count'] = InformRead.objects.filter(inform_id=instance.id).count()
        return Response(data=data)


class ReadInformView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReadInformSerializer(data=request.data)
        if serializer.is_valid():
            inform_pk = serializer.validated_data['inform_pk']
            if InformRead.objects.filter(inform_id=inform_pk, user_id=self.request.user.uid).exists():
                return Response()
            else:
                try:
                    InformRead.objects.create(inform_id=inform_pk, user_id=self.request.user.uid)
                except Exception as e:
                    print(e)
                    return Response(data={'detail': '阅读失败'}, status=status.HTTP_400_BAD_REQUEST)
                return Response()
        else:
            return Response(data={'detail': list(serializer.errors.values())[0][0]}, status=status.HTTP_400_BAD_REQUEST)
