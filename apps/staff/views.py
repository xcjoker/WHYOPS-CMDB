import json

from django.conf import settings
from django.shortcuts import render
from rest_framework import status, viewsets, exceptions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from apps.oaauth.models import OADepartment, OAUser, UserStatusChoices
from apps.oaauth.serializer import DepartmentSerializer
from .serializers import AddStaffSerializer, ActiveStaffSerializer, StaffUploadSerializer
from rest_framework.response import Response
from django.core.mail import send_mail
from utils import aeser
from django.urls import reverse
from oaback.celery import debug_task
from .tasks import send_mail_task
from django.views import View
from django.http.response import JsonResponse
from urllib import parse
from rest_framework import generics
from apps.oaauth.serializer import UserSerializer
from .paginations import StaffPagination
from rest_framework import viewsets
from rest_framework import mixins
from datetime import datetime
import pandas as pd
from django.http.response import HttpResponse
from django.db import transaction

aes = aeser.AESCipher(settings.SECRET_KEY)


def send_active_email(request, email):
    # 使用AES加密邮件

    token = aes.encrypt(email)
    # /staff/active/?token=xxx
    active_path = reverse('staff:active_staff') + '?' + parse.urlencode({'token': token})  # parse处理+号问题
    active_url = request.build_absolute_uri(active_path)
    message = f'请点击以下激活链接激活账号: {active_url}'
    subject = f'【WHYOPS】账号激活'
    # send_mail(subject, recipient_list=[email], message=message, from_email=settings.DEFAULT_FROM_EMAIL)
    send_mail_task.delay(email, subject, message)


# Create your views here.

class DepartmentViewSet(ListAPIView):
    serializer_class = DepartmentSerializer
    queryset = OADepartment.objects.all()


class ActiveStaffView(View):
    def get(self, request):
        # 获取token
        token = request.GET.get('token')
        response = render(request, template_name='active.html')
        response.set_cookie('token', token)
        return response

    def post(self, request, *args, **kwargs):  # 这里的request是django的。不是drf的
        try:
            token = request.COOKIES['token']
            email = aes.decrypt(token)
            serializer = ActiveStaffSerializer(data=request.POST)
            if serializer.is_valid():
                form_email = serializer.validated_data['email']
                user = serializer.validated_data['user']
                if email != form_email:
                    return JsonResponse({'code': 400, 'message': '邮箱错误!'})
                user.status = UserStatusChoices.ACTIVED
                user.save()
                return JsonResponse({'code': 200, 'message': ''})
            else:
                detail = list(serializer.errors.values())[0][0]
                return JsonResponse({'code': 400, 'message': detail})

        except Exception as e:
            return JsonResponse({'code': 400, 'message': 'token错误!'})


class StaffViewSet(
    viewsets.GenericViewSet,  # 拿来自动生成路由的
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin
):
    queryset = OAUser.objects.all()
    pagination_class = StaffPagination

    def get_serializer_class(self):
        if self.request.method in ['GET', 'PUT']:
            return UserSerializer
        else:
            return AddStaffSerializer

    def get_queryset(self):
        department_id = self.request.query_params.get('department_id')
        realname = self.request.query_params.get('realname')
        date_join = self.request.query_params.getlist('data_join[]')

        queryset = self.queryset
        user = self.request.user
        allowed_departments = ['董事会', '运维部']
        if user.department.name not in allowed_departments:
            raise exceptions.PermissionDenied()

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if realname:
            queryset = queryset.filter(realname__icontains=realname)  # icontains表示不区分大小写
        if date_join:
            try:
                start_date = datetime.strptime(date_join[0], "%Y-%m-%d")
                end_date = datetime.strptime(date_join[1], "%Y-%m-%d")
                queryset = queryset.filter(date_joined__range=(start_date, end_date))
            except Exception:
                pass
        return queryset.order_by("-date_joined").all()


    def create(self, request, *args, **kwargs):
        # 如果是用的视图集，那么视图会自动把request放到context中国
        # 如果是APIView，则需要手动
        serializer = AddStaffSerializer(data=request.data, context={'request': request})
        department_id = request.data.get('department_id')
        department = OADepartment.objects.get(id=department_id)
        if serializer.is_valid():
            realname = serializer.validated_data.get('realname')
            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')

            # user = OAUser.objects.create(email=email, realname=realname)
            # user.set_password(password)
            # user.save()

            user = OAUser.objects.create_user(email=email, realname=realname, password=password, department=department)
            user.save()

            send_active_email(request, email)

            return Response()
        else:
            return Response(data={'detail': list(serializer.errors.values())[0][0]}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)




class StaffDownloadView(APIView):
    def get(self, request):
        pks = request.query_params.get('pks')
        try:
            pks = json.loads(pks)
        except Exception:
            print('你到这里了')
            return Response({'detail': '员工参数错误'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current_user = request.user
            queryset = OAUser.objects
            depart = ['董事会', '运维部']
            if current_user.department.name not in depart:
                return Response({'detail': '没有权限下载'}, status=status.HTTP_403_FORBIDDEN)
            queryset = queryset.filter(pk__in=pks)
            result = queryset.values('realname', 'email', 'department__name', 'date_joined', 'status')  # 告诉数据库要查找什么字段
            staff_df = pd.DataFrame(list(result))
            staff_df = staff_df.rename(
                columns={'realname': '姓名', 'email': '邮箱', 'department__name': '部门', 'data_joined': '入职时期',
                         'status': '状态'})
            response = HttpResponse(content_type='application/xlsx')
            response['Content-Disposition'] = "attachment; filename='员工信息.xlsx'"
            # 把staff_df写入到Response中
            with pd.ExcelWriter(response) as writer:
                staff_df.to_excel(writer, sheet_name='员工信息')
            return response
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffUploadView(APIView):
    def post(self, request):
        serializer = StaffUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            current_user = request.user
            depart = ['董事会', '运维部']
            if current_user.department.name not in depart:
                return Response({'detail': '没有权限访问'}, status=status.HTTP_403_FORBIDDEN)

            staff_df = pd.read_excel(file)
            users = []
            for index, row in staff_df.iterrows():
                if current_user.department.name != '董事会':
                    department = current_user.department
                else:
                    try:
                        department = OADepartment.objects.filter(name=row['部门'].first())
                        if not department:
                            return Response({'detail': f"{row['部门']}不存在!"}, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        return Response({'detail': '部门列不存在'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    email = row['邮箱']
                    realname = row['姓名']
                    password = '111111'
                    user = OAUser(email=email, realname=realname, department=department, password=password,
                                  status=UserStatusChoices.UNACTIVE)
                    user.set_password(password)
                    users.append(user)
                except Exception as e:
                    return Response({'detail': '请检查文件中的邮箱，姓名，部门名称!'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                # 原子操作
                with transaction.atomic():
                    OAUser.objects.bulk_create(users)
            except Exception as e:
                return Response({'detail': '员工数据添加错误'}, status=status.HTTP_400_BAD_REQUEST)
            for user in users:
                send_active_email(request, user.email)
            return Response()

        else:
            detail = list(serializer.errors.values())[0][0]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


class TestCeleryView(APIView):
    def get(self, request):
        debug_task.delay()
        return Response({'detail': '成功!'})
