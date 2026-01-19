from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import IdcRegion, IdcServer


class IdcRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdcRegion
        fields = '__all__'

    def validate_address(self, value):
        print(self.context)
        request = self.context.get('request')
        if request and request.method == 'POST':
            if IdcRegion.objects.filter(address=value).exists():
                raise serializers.ValidationError("该地址已经存在!")
        return value


class IdcServerSerializer(serializers.ModelSerializer):
    # password 设为 write_only，确保不会在接口返回中泄露
    password = serializers.CharField(write_only=True, required=True)
    func = serializers.CharField(source='function', required=True)
    region = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = IdcServer
        fields = ['password', 'ip', 'func', 'region']

    def validate_ip(self, value):
        """
        验证 IP 是否已存在
        value: 前端传来的 ip 值
        """
        # 1. 检查数据库中是否已存在该 IP
        # 注意：这里排除当前实例（如果是更新操作，自己不跟自己冲突）
        # 如果你只做【创建】操作，可以直接写 IdcServer.objects.filter(ip=value).exists()

        # 判断是否存在
        print(value)
        if IdcServer.objects.filter(ip=value).exists():
            print('ip错误')
            # 手动构造一个 400 错误，且 detail 是纯字符串
            exc = APIException("IP地址已存在")
            exc.status_code = 400
            exc.detail = "IP地址已存在"  # 强行赋值字符串
            raise exc

        # 2. (可选) 这里还可以加一个正则验证，确保是合法的 IP 格式
        # import re
        # if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        #     raise serializers.ValidationError("IP地址格式不正确")

        return value


class GetIdcServerSerializer(serializers.ModelSerializer):
    region = serializers.SerializerMethodField()  # 使用 SerializerMethodField 来调用自定义方法

    class Meta:
        model = IdcServer
        fields = '__all__'

    def get_region(self, obj):
        return obj.region.address  # 假设 region 是一个外键，address 是区域名称


class IdcServerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdcServer
        fields = ['id', 'scan_status']
