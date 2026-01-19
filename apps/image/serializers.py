from rest_framework import serializers
from django.core.validators import FileExtensionValidator, get_available_image_extensions  #


# get_available_image_extensions包含的更全


class UploadedImageSerializer(serializers.Serializer):
    image = serializers.ImageField(
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif'])],
        error_messages={'required': '请上传图片!', 'invalid_image': '请上传正确格式的图片!'}
    )

    def validate_image(self, value):
        max_size = 5 * 1024 * 1024  # 5M
        size = value.size
        if size > max_size:
            raise serializers.ValidationError('图片最大不能超过5M!')
        return value
