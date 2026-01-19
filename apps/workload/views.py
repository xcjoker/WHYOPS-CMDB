import json
import logging
import yaml
from datetime import datetime, timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from kubernetes import client, config as k8s_config
from apps.clusterInfo.models import Cluster
from kubernetes.client import BatchV1Api, BatchV1beta1Api

from .serializer import PodListSerializer

logger = logging.getLogger(__name__)


def get_k8s_clients(cluster_id):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        config_dict = yaml.safe_load(cluster.kubeconfig)

        client_configuration = client.Configuration()
        k8s_config.load_kube_config_from_dict(
            config_dict,
            client_configuration=client_configuration
        )

        # 优化：减少重试
        client_configuration.retries = 0

        api_client = client.ApiClient(configuration=client_configuration)

        # 优化：5秒健康检查
        try:
            version_api = client.VersionApi(api_client)
            version_api.get_code(_request_timeout=3)
        except Exception as e:
            logger.error(f"Cluster {cluster_id} connection timed out: {e}")
            raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

        # 动态获取 v1beta1 类
        BetaClass = getattr(client, "BatchV1beta1Api", None)
        v1beta1_client = BetaClass(api_client) if BetaClass else None

        # 创建 BatchV1 实例
        batch_v1_client = client.BatchV1Api(api_client)

        return {
            'core': client.CoreV1Api(api_client),  # Pod, Node, SVC
            'apps': client.AppsV1Api(api_client),  # Deploy, DS, STS
            'batch': batch_v1_client,  # Job 代码可能用这个 Key
            'v1': batch_v1_client,  # CronJob 代码用这个 Key (指向同一个对象)
            'v1beta1': v1beta1_client,  # CronJob 旧版本兼容
            'custom': client.CustomObjectsApi(api_client)  # pod指标
        }

    except Cluster.DoesNotExist:
        raise Exception(f"ID为 {cluster_id} 的集群不存在")
    except Exception as e:
        raise Exception(f"K8s连接失败: {str(e)}")


class PodViewSet(viewsets.ViewSet):
    def get_k8s_clients(self, cluster_id):
        """辅助函数：根据 cluster_id 获取 K8s 客户端连接 (带 5s 超时检测)"""
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            # 1. 加载配置
            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 【优化点1】减少底层重试次数
            client_configuration.retries = 0

            api_client = client.ApiClient(configuration=client_configuration)

            # 【优化点2】主动发起 5秒 超时检测
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=3)
            except Exception as e:
                # 记录日志并抛出更友好的错误信息
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

            return {
                'core': client.CoreV1Api(api_client),
                'custom': client.CustomObjectsApi(api_client)
            }
        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            # 这里的异常最终会返回 500 给前端
            raise Exception(f"K8s连接失败: {str(e)}")

    def parse_cpu(self, value):
        """将 CPU 字符串转换为核心数 (float)"""
        if not value: return 0.0
        # 1000m = 1 core
        if value.endswith('m'):
            return float(value[:-1]) / 1000
        # 1000000000n = 1 core
        if value.endswith('n'):
            return float(value[:-1]) / 1000000000
        # 1 = 1 core
        return float(value)

    def parse_memory(self, value):
        """将内存字符串转换为 MiB (float)"""
        if not value: return 0.0
        if value.endswith('Ki'):
            return float(value[:-2]) / 1024
        if value.endswith('Mi'):
            return float(value[:-2])
        if value.endswith('Gi'):
            return float(value[:-2]) * 1024
        if value.endswith('Ti'):
            return float(value[:-2]) * 1024 * 1024
        # 纯数字通常是 bytes
        return float(value) / 1024 / 1024

    def get_pod_real_status(self, pod):
        # 1. 检查是否正在删除
        if pod.metadata.deletion_timestamp:
            return "Terminating"

        # 收集所有容器的状态 (包括初始化容器)
        all_statuses = []
        if pod.status.init_container_statuses:
            all_statuses.extend(pod.status.init_container_statuses)
        if pod.status.container_statuses:
            all_statuses.extend(pod.status.container_statuses)

        # 2. 遍历检查容器异常
        for status in all_statuses:
            if status.state.waiting:
                reason = status.state.waiting.reason
                if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError"]:
                    return reason

            if status.state.terminated and status.state.terminated.exit_code != 0:
                # 例如 OOMKilled, Error
                return status.state.terminated.reason or "Error"

        # 3. 如果没有具体的容器级错误，返回 Pod 的大状态 (Running, Pending, Succeeded)
        return pod.status.phase

        # ================= 核心 LIST 方法 =================

    def list(self, request):
        """
            获取 Pod 列表 (包含资源使用率)
            GET /api/workload/pods/?cluster_id=1&namespace=default
            """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']
            custom_api = apis['custom']

            # 1. 获取 Pod 列表
            if namespace == 'all':
                pod_list = core_api.list_pod_for_all_namespaces()
            else:
                pod_list = core_api.list_namespaced_pod(namespace)

            # 2. 批量获取 Metrics
            metrics_map = {}
            try:
                metrics_data = custom_api.list_cluster_custom_object(
                    group="metrics.k8s.io", version="v1beta1", plural="pods"
                )
                for item in metrics_data.get('items', []):
                    key = f"{item['metadata']['namespace']}/{item['metadata']['name']}"
                    metrics_map[key] = item['containers']
            except Exception as e:
                logger.warning(f"Metrics Server 获取失败: {e}")

            # 3. 组装数据
            data = []
            for pod in pod_list.items:
                name = pod.metadata.name
                ns = pod.metadata.namespace

                # --- 基础信息 ---
                real_status = self.get_pod_real_status(pod)

                age = "Unknown"
                if pod.status.start_time:
                    delta = datetime.now(timezone.utc) - pod.status.start_time
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    elif delta.seconds > 3600:
                        age = f"{delta.seconds // 3600}h"
                    else:
                        age = f"{delta.seconds // 60}m"

                restarts = 0
                ready_count = 0
                total_containers = 0
                if pod.status.container_statuses:
                    total_containers = len(pod.status.container_statuses)
                    for c in pod.status.container_statuses:
                        restarts += c.restart_count
                        if c.ready:
                            ready_count += 1
                ready_str = f"{ready_count}/{total_containers}"

                # 提取容器列表 (供前端日志下拉框使用)
                container_names = []
                if pod.spec.containers:
                    container_names.extend([c.name for c in pod.spec.containers])
                if pod.spec.init_containers:
                    container_names.extend([c.name for c in pod.spec.init_containers])

                # --- 资源计算 (核心优化：Max Percent Strategy) ---

                # 准备该 Pod 的 Metrics 数据
                container_metrics = {}
                m_key = f"{ns}/{name}"
                if m_key in metrics_map:
                    for c_m in metrics_map[m_key]:
                        c_name = c_m['name']
                        container_metrics[c_name] = c_m.get('usage', {})

                # 初始化总计数
                total_cpu_usage = 0.0
                total_mem_usage = 0.0
                total_cpu_limit = 0.0
                total_mem_limit = 0.0

                # 初始化最大百分比 (用于决定进度条颜色)
                max_cpu_percent = 0.0
                max_mem_percent = 0.0

                # 遍历所有容器 (包含 Init 容器，防止 Init 容器 OOM 导致 Pod 挂掉)
                all_containers_spec = pod.spec.containers + (pod.spec.init_containers or [])

                for c_spec in all_containers_spec:
                    # A. 计算 Limit
                    c_cpu_limit = 0.0
                    c_mem_limit = 0.0
                    if c_spec.resources and c_spec.resources.limits:
                        if 'cpu' in c_spec.resources.limits:
                            c_cpu_limit = self.parse_cpu(c_spec.resources.limits['cpu'])
                        if 'memory' in c_spec.resources.limits:
                            c_mem_limit = self.parse_memory(c_spec.resources.limits['memory'])

                    total_cpu_limit += c_cpu_limit
                    total_mem_limit += c_mem_limit

                    # B. 计算 Usage
                    c_cpu_usage = 0.0
                    c_mem_usage = 0.0
                    usage_dict = container_metrics.get(c_spec.name)
                    if usage_dict:
                        c_cpu_usage = self.parse_cpu(usage_dict.get('cpu', '0'))
                        c_mem_usage = self.parse_memory(usage_dict.get('memory', '0'))

                    total_cpu_usage += c_cpu_usage
                    total_mem_usage += c_mem_usage

                    # C. 计算该容器的风险百分比，并更新最大值
                    # CPU
                    if c_cpu_limit > 0:
                        c_cpu_p = (c_cpu_usage / c_cpu_limit) * 100
                        if c_cpu_p > max_cpu_percent:
                            max_cpu_percent = c_cpu_p

                    # Memory
                    if c_mem_limit > 0:
                        c_mem_p = (c_mem_usage / c_mem_limit) * 100
                        if c_mem_p > max_mem_percent:
                            max_mem_percent = c_mem_p

                data.append({
                    "name": name,
                    "namespace": ns,
                    "status": real_status,
                    "ready": ready_str,
                    "ip": pod.status.pod_ip,
                    "node": pod.spec.node_name,
                    "restarts": restarts,
                    "age": age,
                    "containers": container_names,  # 返回容器列表
                    "cpu": {
                        "usage": round(total_cpu_usage, 3),  # 显示总用量
                        "limit": round(total_cpu_limit, 2),  # 显示总限制
                        "percent": round(max_cpu_percent, 1)  # 【关键】使用最大单体风险值
                    },
                    "memory": {
                        "usage": round(total_mem_usage, 1),  # 显示总用量
                        "limit": round(total_mem_limit, 1),  # 显示总限制
                        "percent": round(max_mem_percent, 1)  # 【关键】使用最大单体风险值
                    }
                })

            serializer = PodListSerializer(data, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"获取 Pod 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 新增：YAML 查看与更新接口 ---
    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
        """
        获取或更新 Pod 的 YAML
        GET: /api/workload/pods/yaml/?cluster_id=1&namespace=default&name=my-pod
        PUT: /api/workload/pods/yaml/ (body: {cluster_id, namespace, name, content})
        """
        # 1. 获取通用参数
        if request.method == 'GET':
            cluster_id = request.query_params.get('cluster_id')
            namespace = request.query_params.get('namespace')
            pod_name = request.query_params.get('name')
        else:
            cluster_id = request.data.get('cluster_id')
            namespace = request.data.get('namespace')
            pod_name = request.data.get('name')

        if not all([cluster_id, namespace, pod_name]):
            return Response({"detail": "缺少必要参数 (cluster_id, namespace, name)"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']
            api_client = core_api.api_client

            # === GET: 获取 YAML ===
            if request.method == 'GET':
                # 获取 Pod 对象
                pod_obj = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)

                # 关键步骤：将 K8s 模型对象转为纯字典
                pod_dict = api_client.sanitize_for_serialization(pod_obj)

                # 清理干扰字段 (managedFields 使得 YAML 非常冗长且难读，通常不需要展示)
                if 'metadata' in pod_dict and 'managedFields' in pod_dict['metadata']:
                    del pod_dict['metadata']['managedFields']

                # 转换为 YAML 字符串
                yaml_str = yaml.safe_dump(pod_dict, default_flow_style=False)
                return Response({'content': yaml_str})

            # === PUT: 更新 YAML ===
            elif request.method == 'PUT':
                yaml_content = request.data.get('content')
                if not yaml_content:
                    return Response({"detail": "YAML 内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)

                # 将 YAML 字符串解析回 字典
                try:
                    new_pod_body = yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    return Response({"detail": f"YAML 格式错误: {e}"}, status=status.HTTP_400_BAD_REQUEST)

                # 执行更新 (Replace 操作)
                # 注意：K8s 对 Pod 的修改有很多限制（很多字段是不可变的），
                # 如果用户修改了不可变字段，这里会抛出 ApiException，我们捕获后直接返回给前端提示
                core_api.replace_namespaced_pod(
                    name=pod_name,
                    namespace=namespace,
                    body=new_pod_body
                )

                return Response({'detail': 'Pod 更新成功'}, status=status.HTTP_200_OK)

        except client.exceptions.ApiException as e:
            # 解析 K8s 返回的详细错误信息 (通常在 body 里)
            error_msg = str(e)
            if e.body:
                try:
                    body_json = json.loads(e.body)
                    error_msg = body_json.get('message', error_msg)
                except:
                    pass
            logger.error(f"K8s API 操作失败: {error_msg}")
            return Response({"detail": f"K8s操作失败: {error_msg}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"系统错误: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 查看日志接口
    @action(detail=False, methods=['get'])
    def logs(self, request):
        """
        获取 Pod 日志
        GET /api/workload/pods/logs/?cluster_id=1&namespace=default&name=my-pod&container=nginx
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace')
        pod_name = request.query_params.get('name')
        container_name = request.query_params.get('container') or None
        print('容器名字是:', container_name)

        if not all([cluster_id, namespace, pod_name]):
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            # 调用 K8s API 获取日志
            # tail_lines=1000: 只看最后1000行，避免日志过大
            # timestamps=True: 显示时间戳
            log_content = core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container_name,
                tail_lines=1000,
                timestamps=True
            )

            return Response({'logs': log_content})

        except client.exceptions.ApiException as e:
            # 常见错误处理：比如容器还在创建中，没有日志
            if e.status == 400:
                return Response({'logs': "容器未就绪，暂无日志..."}, status=status.HTTP_200_OK)
            return Response({"detail": f"获取日志失败: {e.reason}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """
        创建 Pod
        POST /api/workload/pods/
        Body: { "cluster_id": 1, "yaml": "..." }
        """
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')

        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少 cluster_id 或 yaml 内容"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 解析 YAML 字符串为 Python 字典
            yaml_content = yaml_content.replace('\t', '  ')
            try:
                pod_data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                return Response({"detail": f"YAML 格式错误: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            if not pod_data or not isinstance(pod_data, dict):
                return Response({"detail": "无效的 YAML 内容"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. 确定 Namespace (优先使用 YAML 里定义的，如果没有则默认为 'default')
            # 注意：Metadata 里的 namespace 优先级最高
            metadata = pod_data.get('metadata', {})
            namespace = metadata.get('namespace', 'default')

            # 3. 连接 K8s
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            # 4. 调用 API 创建
            core_api.create_namespaced_pod(namespace=namespace, body=pod_data)

            pod_name = metadata.get('name', 'unknown')
            return Response({"detail": f"Pod {pod_name} 创建指令已发送"}, status=status.HTTP_201_CREATED)

        except client.exceptions.ApiException as e:
            # 捕获 K8s API 错误 (如资源已存在、参数校验失败)
            error_msg = str(e)
            if e.body:
                try:
                    import json
                    body_json = json.loads(e.body)
                    error_msg = body_json.get('message', error_msg)
                except:
                    pass
            return Response({"detail": f"创建失败: {error_msg}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"系统错误: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """
        删除 Pod
        DELETE /api/workload/pods/{name}/?cluster_id=1&namespace=default
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        pod_name = pk  # DRF 会自动把 URL 里的 ID 解析为 pk

        if not cluster_id or not pod_name:
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            # 调用 K8s API 删除 Pod
            core_api.delete_namespaced_pod(
                name=pod_name,
                namespace=namespace
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except client.exceptions.ApiException as e:
            # 如果 Pod 已经被删除了，也视为成功 (404 Not Found)
            if e.status == 404:
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response({"detail": f"删除失败: {e.reason}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeploymentViewSet(viewsets.ViewSet):

    def get_k8s_clients(self, cluster_id):
        """
        辅助函数：根据 cluster_id 获取 K8s 客户端连接
        (包含 5秒 超时检测，防止集群不通时前端卡死)
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            # 1. 加载配置
            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 【优化点1】减少底层重试次数 (默认是3次)
            client_configuration.retries = 0

            api_client = client.ApiClient(configuration=client_configuration)

            # 【优化点2】主动发起 5秒 超时检测
            # 使用最轻量的 /version 接口测试连接
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=3)
            except Exception as e:
                # 记录日志，并抛出给前端能看懂的错误
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

            return {
                'core': client.CoreV1Api(api_client),
                'apps': client.AppsV1Api(api_client)  # Deployment/StatefulSet/DaemonSet 需要
            }

        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            # 这里的异常会被外层的 try-catch 捕获，最终返回 500
            raise Exception(f"K8s连接失败: {str(e)}")

    def list(self, request):
        """
        获取 Deployment 列表
        GET /api/workload/deployments/?cluster_id=1&namespace=default
        """
        print('过来了')
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            if namespace == 'all':
                d_list = apps_api.list_deployment_for_all_namespaces()
            else:
                d_list = apps_api.list_namespaced_deployment(namespace)

            data = []
            for d in d_list.items:
                # 计算副本状态
                replicas = d.spec.replicas or 0
                available = d.status.available_replicas or 0
                updated = d.status.updated_replicas or 0

                # 简单的状态判断
                status_phase = "Running"
                if available < replicas:
                    status_phase = "Progressing"  # 或 Warning
                if available == 0 and replicas > 0:
                    status_phase = "Failed"

                # 存活时间
                age = "Unknown"
                if d.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - d.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                # 镜像列表
                images = []
                if d.spec.template.spec.containers:
                    images = [c.image for c in d.spec.template.spec.containers]

                data.append({
                    "name": d.metadata.name,
                    "namespace": d.metadata.namespace,
                    "status": status_phase,
                    "replicas": replicas,  # 期望副本数
                    "available": available,  # 可用副本数
                    "up_to_date": updated,  # 已更新副本数
                    "images": images,
                    "age": age,
                    "labels": d.metadata.labels
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 Deployment 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def scale(self, request):
        """
        扩缩容接口
        POST /api/workload/deployments/scale/
        Body: { "cluster_id": 1, "namespace": "default", "name": "nginx", "replicas": 3 }
        """
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')
        replicas = request.data.get('replicas')

        if not all([cluster_id, namespace, name]) or replicas is None:
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            # 使用 patch 方法只修改 replicas
            body = {"spec": {"replicas": int(replicas)}}
            apps_api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body
            )
            return Response({"detail": f"已将 {name} 副本数调整为 {replicas}"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def restart(self, request):
        """
        滚动重启接口
        POST /api/workload/deployments/restart/
        原理：修改 annotation 触发滚动更新
        """
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            # Patch 一个时间戳 annotation 强制 Pod 重建
            now = datetime.now(timezone.utc).isoformat()
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": now
                            }
                        }
                    }
                }
            }
            apps_api.patch_namespaced_deployment(name, namespace, body)
            return Response({"detail": f"Deployment {name} 已触发滚动重启"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """
        创建 Deployment
        POST /api/workload/deployments/
        Body: { "cluster_id": 1, "yaml": "..." }
        """
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')

        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少 cluster_id 或 yaml 内容"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 解析 YAML
            yaml_content = yaml_content.replace('\t', '  ')
            try:
                dp_data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                return Response({"detail": f"YAML 格式错误: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            if not dp_data or not isinstance(dp_data, dict):
                return Response({"detail": "无效的 YAML 内容"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. 确定 Namespace
            metadata = dp_data.get('metadata', {})
            namespace = metadata.get('namespace', 'default')

            # 3. 连接 K8s (AppsV1)
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            # 4. 创建资源
            apps_api.create_namespaced_deployment(namespace=namespace, body=dp_data)

            dp_name = metadata.get('name', 'unknown')
            return Response({"detail": f"Deployment {dp_name} 创建指令已发送"}, status=status.HTTP_201_CREATED)

        except client.exceptions.ApiException as e:
            error_msg = str(e)
            if e.body:
                try:
                    body_json = json.loads(e.body)
                    error_msg = body_json.get('message', error_msg)
                except:
                    pass
            return Response({"detail": f"创建失败: {error_msg}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"系统错误: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
        """
        获取或更新 Deployment 的 YAML
        """
        if request.method == 'GET':
            cluster_id = request.query_params.get('cluster_id')
            namespace = request.query_params.get('namespace')
            name = request.query_params.get('name')
        else:
            cluster_id = request.data.get('cluster_id')
            namespace = request.data.get('namespace')
            name = request.data.get('name')

        if not all([cluster_id, namespace, name]):
            return Response({"detail": "缺少必要参数 (cluster_id, namespace, name)"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            # === GET: 获取 YAML ===
            if request.method == 'GET':
                dp_obj = apps_api.read_namespaced_deployment(name=name, namespace=namespace)

                # 序列化为字典
                dp_dict = apps_api.api_client.sanitize_for_serialization(dp_obj)

                # 清理干扰字段
                if 'metadata' in dp_dict and 'managedFields' in dp_dict['metadata']:
                    del dp_dict['metadata']['managedFields']

                yaml_str = yaml.safe_dump(dp_dict, default_flow_style=False)
                return Response({'content': yaml_str})

            # === PUT: 更新 YAML ===
            elif request.method == 'PUT':
                yaml_content = request.data.get('content')
                if not yaml_content:
                    return Response({"detail": "YAML 内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    new_body = yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    return Response({"detail": f"YAML 格式错误: {e}"}, status=status.HTTP_400_BAD_REQUEST)

                apps_api.replace_namespaced_deployment(
                    name=name,
                    namespace=namespace,
                    body=new_body
                )
                return Response({'detail': 'Deployment 更新成功'}, status=status.HTTP_200_OK)

        except client.exceptions.ApiException as e:
            error_msg = str(e)
            if e.body:
                try:
                    body_json = json.loads(e.body)
                    error_msg = body_json.get('message', error_msg)
                except:
                    pass
            logger.error(f"K8s操作失败: {error_msg}")
            return Response({"detail": f"K8s操作失败: {error_msg}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """
        删除 Deployment
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk

        if not cluster_id or not name:
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            apps_api.delete_namespaced_deployment(
                name=name,
                namespace=namespace
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except client.exceptions.ApiException as e:
            if e.status == 404:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({"detail": f"删除失败: {e.reason}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StatefulSetViewSet(viewsets.ViewSet):
    def get_k8s_clients(self, cluster_id):
        """
        辅助函数：根据 cluster_id 获取 K8s 客户端连接
        (包含 5秒 超时检测，防止集群不通时前端卡死)
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            # 1. 加载配置
            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 【优化点1】减少底层重试次数 (默认是3次)
            client_configuration.retries = 0

            api_client = client.ApiClient(configuration=client_configuration)

            # 【优化点2】主动发起 5秒 超时检测
            # 使用最轻量的 /version 接口测试连接
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=3)
            except Exception as e:
                # 记录日志，并抛出给前端能看懂的错误
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

            return {
                'core': client.CoreV1Api(api_client),
                'apps': client.AppsV1Api(api_client)  # Deployment/StatefulSet/DaemonSet 需要
            }

        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            # 这里的异常会被外层的 try-catch 捕获，最终返回 500
            raise Exception(f"K8s连接失败: {str(e)}")

    def list(self, request):
        """
        获取 StatefulSet 列表
        GET /api/workload/statefulsets/?cluster_id=1&namespace=default
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            if namespace == 'all':
                sts_list = apps_api.list_stateful_set_for_all_namespaces()
            else:
                sts_list = apps_api.list_namespaced_stateful_set(namespace)

            data = []
            for sts in sts_list.items:
                # StatefulSet 的状态字段
                replicas = sts.spec.replicas or 0
                ready = sts.status.ready_replicas or 0
                current = sts.status.current_replicas or 0  # 当前版本副本数

                # 状态判断
                status_phase = "Running"
                if ready < replicas:
                    status_phase = "Progressing"
                if ready == 0 and replicas > 0:
                    status_phase = "Failed"

                # 存活时间
                age = "Unknown"
                if sts.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - sts.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                # 镜像
                images = []
                if sts.spec.template.spec.containers:
                    images = [c.image for c in sts.spec.template.spec.containers]

                data.append({
                    "name": sts.metadata.name,
                    "namespace": sts.metadata.namespace,
                    "status": status_phase,
                    "replicas": replicas,
                    "ready": ready,
                    "current": current,
                    "images": images,
                    "age": age,
                    "service_name": sts.spec.service_name  # StatefulSet 特有
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 StatefulSet 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def scale(self, request):
        """扩缩容"""
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')
        replicas = request.data.get('replicas')

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']
            body = {"spec": {"replicas": int(replicas)}}
            apps_api.patch_namespaced_stateful_set(name, namespace, body)
            return Response({"detail": f"已将 {name} 副本数调整为 {replicas}"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def restart(self, request):
        """滚动重启"""
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']
            now = datetime.now(timezone.utc).isoformat()
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": now
                            }
                        }
                    }
                }
            }
            apps_api.patch_namespaced_stateful_set(name, namespace, body)
            return Response({"detail": f"StatefulSet {name} 已触发滚动重启"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            sts_data = yaml.safe_load(yaml_content)
            namespace = sts_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)
            apis['apps'].create_namespaced_stateful_set(namespace, sts_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # 这里省略详细错误解析，建议复用之前的 parse_k8s_error 逻辑
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            apis['apps'].delete_namespaced_stateful_set(name, namespace)
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
            apps_api = apis['apps']

            if request.method == 'GET':
                obj = apps_api.read_namespaced_stateful_set(name, namespace)
                data_dict = apps_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                apps_api.replace_namespaced_stateful_set(name, namespace, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DaemonSetViewSet(viewsets.ViewSet):
    def get_k8s_clients(self, cluster_id):
        """
        辅助函数：根据 cluster_id 获取 K8s 客户端连接
        (包含 5秒 超时检测，防止集群不通时前端卡死)
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            # 1. 加载配置
            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 【优化点1】减少底层重试次数 (默认是3次)
            client_configuration.retries = 0

            api_client = client.ApiClient(configuration=client_configuration)

            # 【优化点2】主动发起 5秒 超时检测
            # 使用最轻量的 /version 接口测试连接
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=3)
            except Exception as e:
                # 记录日志，并抛出给前端能看懂的错误
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

            return {
                'core': client.CoreV1Api(api_client),
                'apps': client.AppsV1Api(api_client)  # Deployment/StatefulSet/DaemonSet 需要
            }

        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            # 这里的异常会被外层的 try-catch 捕获，最终返回 500
            raise Exception(f"K8s连接失败: {str(e)}")

    def list(self, request):
        """
        获取 DaemonSet 列表
        GET /api/workload/daemonsets/?cluster_id=1&namespace=default
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']

            if namespace == 'all':
                ds_list = apps_api.list_daemon_set_for_all_namespaces()
            else:
                ds_list = apps_api.list_namespaced_daemon_set(namespace)

            data = []
            for ds in ds_list.items:
                # DaemonSet 特有的状态字段
                desired = ds.status.desired_number_scheduled or 0
                current = ds.status.current_number_scheduled or 0
                ready = ds.status.number_ready or 0
                available = ds.status.number_available or 0

                # 状态判断逻辑
                status_phase = "Running"
                if ready < desired:
                    status_phase = "Progressing"  # 正在部署或部分节点失败
                if desired > 0 and ready == 0:
                    status_phase = "Failed"

                # 存活时间
                age = "Unknown"
                if ds.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - ds.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                # 镜像
                images = []
                if ds.spec.template.spec.containers:
                    images = [c.image for c in ds.spec.template.spec.containers]

                data.append({
                    "name": ds.metadata.name,
                    "namespace": ds.metadata.namespace,
                    "status": status_phase,
                    "desired": desired,  # 期望调度节点数
                    "current": current,  # 当前调度节点数
                    "ready": ready,  # 就绪 Pod 数
                    "available": available,
                    "images": images,
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 DaemonSet 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 注意：DaemonSet 没有 Scale 接口，因为它是随节点自动扩缩的

    @action(detail=False, methods=['post'])
    def restart(self, request):
        """滚动重启"""
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')

        try:
            apis = get_k8s_clients(cluster_id)
            apps_api = apis['apps']
            now = datetime.now(timezone.utc).isoformat()
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": now
                            }
                        }
                    }
                }
            }
            apps_api.patch_namespaced_daemon_set(name, namespace, body)
            return Response({"detail": f"DaemonSet {name} 已触发滚动重启"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            ds_data = yaml.safe_load(yaml_content)
            namespace = ds_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)
            apis['apps'].create_namespaced_daemon_set(namespace, ds_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            apis['apps'].delete_namespaced_daemon_set(name, namespace)
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
            apps_api = apis['apps']

            if request.method == 'GET':
                obj = apps_api.read_namespaced_daemon_set(name, namespace)
                data_dict = apps_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                apps_api.replace_namespaced_daemon_set(name, namespace, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JobViewSet(viewsets.ViewSet):
    def get_k8s_clients(self, cluster_id):
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 优化：减少重试
            client_configuration.retries = 0

            api_client = client.ApiClient(configuration=client_configuration)

            # 优化：5秒健康检查
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=3)
            except Exception as e:
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (3s) 或不可达，请检查集群网络状态。")

            # 动态获取 v1beta1 类
            BetaClass = getattr(client, "BatchV1beta1Api", None)
            v1beta1_client = BetaClass(api_client) if BetaClass else None

            # 创建 BatchV1 实例
            batch_v1_client = client.BatchV1Api(api_client)

            return {
                'core': client.CoreV1Api(api_client),  # Pod, Node, SVC
                'apps': client.AppsV1Api(api_client),  # Deploy, DS, STS
                'batch': batch_v1_client,  # Job 代码可能用这个 Key
                'v1': batch_v1_client,  # CronJob 代码用这个 Key (指向同一个对象)
                'v1beta1': v1beta1_client,  # CronJob 旧版本兼容
                'custom': client.CustomObjectsApi(api_client)
            }

        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            raise Exception(f"K8s连接失败: {str(e)}")

    def list(self, request):
        """
        获取 Job 列表
        GET /api/workload/jobs/?cluster_id=1&namespace=default
        """
        print('获取job')
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            batch_api = apis['batch']

            if namespace == 'all':
                job_list = batch_api.list_job_for_all_namespaces()
            else:
                job_list = batch_api.list_namespaced_job(namespace)

            data = []
            for job in job_list.items:
                # 状态统计
                active = job.status.active or 0
                succeeded = job.status.succeeded or 0
                failed = job.status.failed or 0
                completions = job.spec.completions or 1  # 目标完成数

                # 状态判断
                status_phase = "Running"
                if succeeded >= completions:
                    status_phase = "Completed"
                elif failed > 0:
                    # 简单判断，如果有失败且没活跃，可能就是 Failed
                    if active == 0:
                        status_phase = "Failed"
                    else:
                        status_phase = "Running (Retrying)"  # 还在重试

                # 计算耗时 (Duration)
                duration = "--"
                start_time = job.status.start_time
                completion_time = job.status.completion_time

                if start_time and completion_time:
                    delta = completion_time - start_time
                    duration = str(delta).split('.')[0]  # 去掉微秒
                elif start_time:
                    # 还在运行中，计算当前耗时
                    delta = datetime.now(timezone.utc) - start_time
                    duration = f"{delta.days}d {delta.seconds // 3600}h" if delta.days > 0 else f"{delta.seconds // 60}m"

                # 存活时间 (Age)
                age = "Unknown"
                if job.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - job.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                # 镜像
                images = []
                if job.spec.template.spec.containers:
                    images = [c.image for c in job.spec.template.spec.containers]

                data.append({
                    "name": job.metadata.name,
                    "namespace": job.metadata.namespace,
                    "status": status_phase,
                    "completions": f"{succeeded}/{completions}",
                    "active": active,
                    "failed": failed,
                    "duration": duration,
                    "images": images,
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 Job 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            job_data = yaml.safe_load(yaml_content)
            namespace = job_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)
            apis['batch'].create_namespaced_job(namespace, job_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除 (默认由 K8s 级联删除 Pod)"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            # propagation_policy='Background' 确保级联删除 Pod
            apis['batch'].delete_namespaced_job(
                name,
                namespace,
                propagation_policy='Background'
            )
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
            batch_api = apis['batch']

            if request.method == 'GET':
                obj = batch_api.read_namespaced_job(name, namespace)
                data_dict = batch_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                batch_api.replace_namespaced_job(name, namespace, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CronJobViewSet(viewsets.ViewSet):
    def get_k8s_clients(self, cluster_id):
        """
        【最终修复版】获取 K8s 客户端连接
        修复点：同时返回 'batch' 和 'v1' 两个Key，防止 CronJob 代码报 KeyError: 'v1'
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            config_dict = yaml.safe_load(cluster.kubeconfig)

            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )

            # 优化：减少重试
            client_configuration.retries = 1

            api_client = client.ApiClient(configuration=client_configuration)

            # 优化：5秒健康检查
            try:
                version_api = client.VersionApi(api_client)
                version_api.get_code(_request_timeout=5)
            except Exception as e:
                logger.error(f"Cluster {cluster_id} connection timed out: {e}")
                raise Exception("集群连接超时 (5s) 或不可达，请检查集群网络状态。")

            # 动态获取 v1beta1 类
            BetaClass = getattr(client, "BatchV1beta1Api", None)
            v1beta1_client = BetaClass(api_client) if BetaClass else None

            # 创建 BatchV1 实例
            batch_v1_client = client.BatchV1Api(api_client)

            return {
                # --- 核心常用 ---
                'core': client.CoreV1Api(api_client),  # Pod, Node, SVC
                'apps': client.AppsV1Api(api_client),  # Deploy, DS, STS

                # --- 批处理 (关键修复点) ---
                'batch': batch_v1_client,  # Job 代码可能用这个 Key
                'v1': batch_v1_client,  # CronJob 代码用这个 Key (指向同一个对象)
                'v1beta1': v1beta1_client,  # CronJob 旧版本兼容

                # --- 其他 ---
                'networking': client.NetworkingV1Api(api_client),
                'storage': client.StorageV1Api(api_client),
                'custom': client.CustomObjectsApi(api_client)
            }

        except Cluster.DoesNotExist:
            raise Exception(f"ID为 {cluster_id} 的集群不存在")
        except Exception as e:
            raise Exception(f"K8s连接失败: {str(e)}")

    def list(self, request):
        """
        获取 CronJob 列表 (自动兼容 v1 和 v1beta1)
        """
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)

            # --- 兼容性核心逻辑 ---
            # 1. 先尝试用 batch/v1 (新版)
            cj_list = None
            used_api_version = 'v1'
            try:
                if namespace == 'all':
                    cj_list = apis['v1'].list_cron_job_for_all_namespaces()
                else:
                    cj_list = apis['v1'].list_namespaced_cron_job(namespace)
            except client.exceptions.ApiException as e:
                # 2. 如果报错 404 (Not Found)，说明集群版本老，尝试 batch/v1beta1
                if e.status == 404:
                    used_api_version = 'v1beta1'
                    if namespace == 'all':
                        cj_list = apis['v1beta1'].list_cron_job_for_all_namespaces()
                    else:
                        cj_list = apis['v1beta1'].list_namespaced_cron_job(namespace)
                else:
                    raise e  # 其他错误直接抛出

            data = []
            for cj in cj_list.items:
                schedule = cj.spec.schedule
                suspend = cj.spec.suspend

                # Active Jobs 处理
                active_count = 0
                if cj.status.active:
                    active_count = len(cj.status.active)

                # 时间处理
                last_schedule = "--"
                if cj.status.last_schedule_time:
                    dt = cj.status.last_schedule_time
                    delta = datetime.now(timezone.utc) - dt
                    if delta.seconds < 60:
                        last_schedule = f"{delta.seconds}s ago"
                    elif delta.seconds < 3600:
                        last_schedule = f"{delta.seconds // 60}m ago"
                    else:
                        last_schedule = f"{delta.seconds // 3600}h ago"

                # Age
                age = "Unknown"
                if cj.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - cj.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                # 镜像获取 (兼容不同层级结构，虽通常一致)
                images = []
                try:
                    containers = cj.spec.job_template.spec.template.spec.containers
                    images = [c.image for c in containers]
                except:
                    pass

                data.append({
                    "name": cj.metadata.name,
                    "namespace": cj.metadata.namespace,
                    "schedule": schedule,
                    "suspend": suspend,
                    "active": active_count,
                    "last_schedule": last_schedule,
                    "images": images,
                    "age": age,
                    "api_version": used_api_version  # 可选：记录使用的版本
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 CronJob 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            cj_data = yaml.safe_load(yaml_content)
            namespace = cj_data.get('metadata', {}).get('namespace', 'default')

            # 自动修正 YAML 中的 apiVersion，防止用户写错
            # 但这里我们主要依赖 Try-Catch 自动降级

            apis = get_k8s_clients(cluster_id)

            try:
                # 尝试 v1
                apis['v1'].create_namespaced_cron_job(namespace, cj_data)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    # 尝试 v1beta1 (同时修正 yaml 里的 apiVersion 声明)
                    cj_data['apiVersion'] = 'batch/v1beta1'
                    apis['v1beta1'].create_namespaced_cron_job(namespace, cj_data)
                else:
                    raise e

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # 简化错误信息
            return Response({"detail": f"创建失败: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            try:
                apis['v1'].delete_namespaced_cron_job(name, namespace)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    # 注意：如果资源不存在也是 404，API 不存在也是 404
                    # 这里尝试调用 beta1，如果 beta1 也 404 说明真没了
                    apis['v1beta1'].delete_namespaced_cron_job(name, namespace)
                else:
                    raise e
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def toggle_suspend(self, request):
        cluster_id = request.data.get('cluster_id')
        namespace = request.data.get('namespace')
        name = request.data.get('name')
        suspend = request.data.get('suspend')

        if not all([cluster_id, namespace, name]) or suspend is None:
            return Response({"detail": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            body = {"spec": {"suspend": suspend}}

            try:
                apis['v1'].patch_namespaced_cron_job(name, namespace, body)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    apis['v1beta1'].patch_namespaced_cron_job(name, namespace, body)
                else:
                    raise e

            action_text = "暂停" if suspend else "恢复"
            return Response({"detail": f"CronJob {name} 已{action_text}"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'put'], url_path='yaml')
    def yaml_handler(self, request):
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

            if request.method == 'GET':
                try:
                    obj = apis['v1'].read_namespaced_cron_job(name, namespace)
                    # 序列化
                    data_dict = apis['v1'].api_client.sanitize_for_serialization(obj)
                except client.exceptions.ApiException as e:
                    if e.status == 404:
                        obj = apis['v1beta1'].read_namespaced_cron_job(name, namespace)
                        data_dict = apis['v1beta1'].api_client.sanitize_for_serialization(obj)
                    else:
                        raise e

                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)

                try:
                    apis['v1'].replace_namespaced_cron_job(name, namespace, body)
                except client.exceptions.ApiException as e:
                    if e.status == 404:
                        # 如果是旧版本 API，可能需要确保 apiVersion 是 v1beta1
                        if body.get('apiVersion') == 'batch/v1':
                            body['apiVersion'] = 'batch/v1beta1'
                        apis['v1beta1'].replace_namespaced_cron_job(name, namespace, body)
                    else:
                        raise e
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
