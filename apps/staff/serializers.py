from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, get_available_image_extensions  #

OAUser = get_user_model()


class AddStaffSerializer(serializers.Serializer):
    realname = serializers.CharField(max_length=100, error_messages={'required': '请输入用户名'})
    email = serializers.EmailField(error_messages={'required': '请输入邮箱', 'invalid': '请输入正确格式的邮箱'})
    password = serializers.CharField(max_length=20, error_messages={'required': '请输入密码!'})

    def validate(self, attrs):
        request = self.context.get('request')
        email = attrs.get('email')
        if OAUser.objects.filter(email=email).exists():
            raise serializers.ValidationError('邮箱已经存在')
        return attrs


class ActiveStaffSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={'required': '请输入邮箱', 'invalid': '请输入正确格式的邮箱'})
    password = serializers.CharField(max_length=20, error_messages={'required': '请输入密码!'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = OAUser.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError('邮箱或者密码错误')
        attrs['user'] = user
        return attrs


class StaffUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        validators=[FileExtensionValidator(['xlsx', 'xls'])],
        error_messages={'required': '请上传文件!'}
    )
