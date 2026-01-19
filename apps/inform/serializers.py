from rest_framework import serializers
from apps.inform.models import Inform, InformRead
from apps.oaauth.serializer import UserSerializer


class InformReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformRead
        fields = '__all__'


class InformSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    reads = InformReadSerializer(many=True, read_only=True)

    class Meta:
        model = Inform
        fields = '__all__'
        # renad_only_fields = ['public', ]

    def create(self, validated_data):
        inform = Inform.objects.create(**validated_data, author=self.context['request'].user)
        return inform


class ReadInformSerializer(serializers.Serializer):
    inform_pk = serializers.IntegerField(error_messages={'required': '请传入inform的id!'})
