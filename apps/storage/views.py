import logging
import yaml
from datetime import datetime, timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from kubernetes import client, config as k8s_config
from apps.clusterInfo.models import Cluster

logger = logging.getLogger(__name__)


def get_k8s_clients(cluster_id):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        config_dict = yaml.safe_load(cluster.kubeconfig)

        # 加载配置
        client_configuration = client.Configuration()
        k8s_config.load_kube_config_from_dict(
            config_dict,
            client_configuration=client_configuration
        )

        # 优化1：减少重试次数，避免底层默认的多次重试导致等待时间过长
        client_configuration.retries = 0

        api_client = client.ApiClient(configuration=client_configuration)

        # 优化2：主动发起一次“轻量级”请求检测连接，强制 5秒超时
        try:
            # 获取集群版本信息接口 (/version) 是最轻量的
            version_api = client.VersionApi(api_client)
            version_api.get_code(_request_timeout=3)
        except Exception as e:
            # 捕获超时或连接拒绝错误，抛出简明的异常信息
            logger.error(f"Cluster {cluster_id} connection timed out: {e}")
            raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

        return {
            'core': client.CoreV1Api(api_client),  # PV 属于 CoreV1
            'storage': client.StorageV1Api(api_client)
        }

    except Cluster.DoesNotExist:
        raise Exception(f"ID为 {cluster_id} 的集群不存在")
    except Exception as e:
        # 这里的异常会被 list/create 等方法捕获并返回给前端
        raise Exception(f"K8s连接失败: {str(e)}")


class PVViewSet(viewsets.ViewSet):

    def list(self, request):
        """
        获取 PV 列表
        GET /api/storage/pvs/?cluster_id=1
        """
        cluster_id = request.query_params.get('cluster_id')
        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            # 获取 PV 列表，本身也设置一个超时，双重保险
            pv_list = core_api.list_persistent_volume(_request_timeout=5)

            data = []
            for pv in pv_list.items:
                # 1. 状态
                status_phase = pv.status.phase  # Available, Bound, Released, Failed

                # 2. 容量
                capacity = pv.spec.capacity.get('storage', '0') if pv.spec.capacity else '0'

                # 3. 访问模式
                access_modes = pv.spec.access_modes or []

                # 4. Claim (绑定到哪个 PVC)
                claim = ""
                if pv.spec.claim_ref:
                    claim = f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}"

                # 5. Age
                age = "Unknown"
                if pv.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - pv.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                data.append({
                    "name": pv.metadata.name,
                    "status": status_phase,
                    "capacity": capacity,
                    "access_modes": access_modes,
                    "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
                    "storage_class": pv.spec.storage_class_name,
                    "claim": claim,
                    "reason": pv.status.reason or "",  # 错误原因
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 PV 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """
        创建 PV
        POST /api/storage/pvs/
        """
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            pv_data = yaml.safe_load(yaml_content)

            apis = get_k8s_clients(cluster_id)
            # create_persistent_volume 不需要 namespace
            apis['core'].create_persistent_volume(body=pv_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        删除 PV
        DELETE /api/storage/pvs/{name}/
        """
        cluster_id = request.query_params.get('cluster_id')
        name = pk

        if not cluster_id or not name:
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apis['core'].delete_persistent_volume(name)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
        """
        获取/更新 YAML
        GET: /api/storage/pvs/yaml/?cluster_id=1&name=pv-name
        PUT: /api/storage/pvs/yaml/ (body: cluster_id, name, content)
        """
        if request.method == 'GET':
            cluster_id = request.query_params.get('cluster_id')
            name = request.query_params.get('name')
        else:
            cluster_id = request.data.get('cluster_id')
            name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            if request.method == 'GET':
                obj = core_api.read_persistent_volume(name)
                data_dict = core_api.api_client.sanitize_for_serialization(obj)
                # 清理 managedFields 以减少干扰
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                core_api.replace_persistent_volume(name, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PVCViewSet(viewsets.ViewSet):
    def list(self, request):
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            if namespace == 'all':
                pvc_list = core_api.list_persistent_volume_claim_for_all_namespaces(_request_timeout=10)
            else:
                pvc_list = core_api.list_namespaced_persistent_volume_claim(namespace, _request_timeout=10)

            data = []
            for pvc in pvc_list.items:
                # 1. 状态
                status_phase = pvc.status.phase  # Bound, Pending, Lost

                # 2. 容量 (从 status 或 spec 获取)
                capacity = "0"
                if pvc.status.capacity and 'storage' in pvc.status.capacity:
                    capacity = pvc.status.capacity['storage']
                elif pvc.spec.resources and pvc.spec.resources.requests:
                    capacity = pvc.spec.resources.requests.get('storage', '0')

                # 3. 绑定的 PV 名称
                volume_name = pvc.spec.volume_name or ""

                # 4. 访问模式
                access_modes = pvc.spec.access_modes or []

                # 5. Age
                age = "Unknown"
                if pvc.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - pvc.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                data.append({
                    "name": pvc.metadata.name,
                    "namespace": pvc.metadata.namespace,
                    "status": status_phase,
                    "volume": volume_name,
                    "capacity": capacity,
                    "access_modes": access_modes,
                    "storage_class": pvc.spec.storage_class_name,
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 PVC 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建 PVC"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            pvc_data = yaml.safe_load(yaml_content)
            namespace = pvc_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)
            apis['core'].create_namespaced_persistent_volume_claim(namespace, pvc_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除 PVC"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            apis['core'].delete_namespaced_persistent_volume_claim(name, namespace)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
        """获取/更新 YAML"""
        if request.method == 'GET':
            cluster_id = request.query_params.get('cluster_id')
            namespace = request.query_params.get('namespace')
            name = request.query_params.get('name')
        else:
            cluster_id = request.data.get('cluster_id')
            namespace = request.data.get('namespace')
            name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            if request.method == 'GET':
                obj = core_api.read_namespaced_persistent_volume_claim(name, namespace)
                data_dict = core_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                core_api.replace_namespaced_persistent_volume_claim(name, namespace, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StorageClassViewSet(viewsets.ViewSet):
    def list(self, request):
        """
        获取 StorageClass 列表
        GET /api/storage/storageclasses/?cluster_id=1
        """
        cluster_id = request.query_params.get('cluster_id')
        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 获取客户端 (自动包含 'storage': StorageV1Api)
            apis = get_k8s_clients(cluster_id)
            storage_api = apis['storage']

            # 2. 调用 K8s API
            sc_list = storage_api.list_storage_class(_request_timeout=10)

            data = []
            for sc in sc_list.items:
                # 提取关键信息
                name = sc.metadata.name
                provisioner = sc.provisioner
                reclaim_policy = sc.reclaim_policy
                binding_mode = sc.volume_binding_mode
                allow_expansion = sc.allow_volume_expansion or False

                # 存活时间
                age = "Unknown"
                if sc.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - sc.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                data.append({
                    "name": name,
                    "provisioner": provisioner,
                    "reclaim_policy": reclaim_policy,
                    "binding_mode": binding_mode,
                    "allow_expansion": allow_expansion,
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 StorageClass 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建 StorageClass"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            sc_data = yaml.safe_load(yaml_content)

            apis = get_k8s_clients(cluster_id)
            apis['storage'].create_storage_class(body=sc_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除 StorageClass"""
        cluster_id = request.query_params.get('cluster_id')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            apis['storage'].delete_storage_class(name)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
        """获取/更新 YAML"""
        if request.method == 'GET':
            cluster_id = request.query_params.get('cluster_id')
            name = request.query_params.get('name')
        else:
            cluster_id = request.data.get('cluster_id')
            name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            storage_api = apis['storage']

            if request.method == 'GET':
                obj = storage_api.read_storage_class(name)
                data_dict = storage_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                storage_api.replace_storage_class(name, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
