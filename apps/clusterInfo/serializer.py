from rest_framework import serializers
from .models import Cluster, Node


class ClusterSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    import_status_display = serializers.CharField(source='get_import_status_display', read_only=True)
    cluster_status_display = serializers.CharField(source='get_cluster_status_display', read_only=True)

    class Meta:
        model = Cluster
        fields = '__all__'

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'  # 序列化所有字段，包括 cpu_cores, disk_total 等



