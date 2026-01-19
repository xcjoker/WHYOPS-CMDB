from rest_framework import serializers


class PodResourceSerializer(serializers.Serializer):
    """资源使用情况序列化：用于 CPU 和 内存"""
    usage = serializers.FloatField(help_text="当前使用量 (CPU核心数 或 内存MiB)")
    limit = serializers.FloatField(help_text="限制量 (0表示无限制)")
    percent = serializers.FloatField(help_text="使用百分比")


class PodListSerializer(serializers.Serializer):
    """Pod 列表信息序列化"""
    name = serializers.CharField()
    namespace = serializers.CharField()
    status = serializers.CharField()
    ip = serializers.CharField(allow_null=True)
    node = serializers.CharField(allow_null=True)
    restarts = serializers.IntegerField()
    age = serializers.CharField()
    containers = serializers.ListField(child=serializers.CharField())

    # 嵌套资源信息，直接复用上面的 Serializer
    cpu = PodResourceSerializer()
    memory = PodResourceSerializer()