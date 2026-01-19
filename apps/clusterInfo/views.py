import json
import os
import time
import yaml
import logging
import requests
from kubernetes.client import ApiException
from rest_framework import viewsets, status
from rest_framework.response import Response
from kubernetes import client, config as k8s_config
from rest_framework.decorators import action

from .models import Cluster, Node
from .serializer import ClusterSerializer, NodeSerializer
from django.utils.dateparse import parse_datetime
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from .tasks import task_sync_cluster_nodes
from .PrometheusHandler import PrometheusHandler

logger = logging.getLogger(__name__)

SOFT_DIR = r'D:\pycharm\oaback\apps\idc\soft'
JSON_FILE_PATH = os.path.join(SOFT_DIR, 'node_exporter_targets.json')
# Prometheus API 地址
PROMETHEUS_API_URL = "http://localhost:9090/api/v1/query"


# ===========================================

# class PrometheusHandler:
#     """
#     处理与 Prometheus 相关的操作：文件注册、查询
#     """
#
#     @staticmethod
#     def remove_targets_from_json(targets_to_remove):
#         if not targets_to_remove or not os.path.exists(JSON_FILE_PATH):
#             return
#
#         try:
#             # 1. 读取文件
#             with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
#                 data = json.load(f)  # data 是一个列表List [ {}, {}, {} ]
#
#             if not data:
#                 return
#
#             original_count = 0
#
#             for job_group in data:
#                 current_targets = job_group.get('targets', [])
#                 original_count += len(current_targets)
#
#                 job_group['targets'] = [t for t in current_targets if t not in targets_to_remove]
#
#             data = [group for group in data if len(group.get('targets', [])) > 0]
#
#             # 4. 写回文件
#             with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
#                 # ensure_ascii=False 保证中文字符（如"集群一"）正常显示，不转义成 \uXXXX
#                 json.dump(data, f, indent=4, ensure_ascii=False)
#
#             print(f"Prometheus 目标清理完成。需移除: {targets_to_remove}")
#
#         except Exception as e:
#             print(f"移除 Prometheus 目标失败: {e}")
#
#     @staticmethod
#     def update_target_file(ip_list, cluster_name):
#         """
#         批量将 IP 列表写入 JSON 文件
#         """
#         if not ip_list:
#             return
#
#         # 1. 读取现有文件
#         target_list = []
#         if os.path.exists(JSON_FILE_PATH):
#             try:
#                 with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
#                     content = f.read()
#                     if content:
#                         target_list = json.loads(content)
#             except Exception as e:
#                 logger.error(f"读取 Prometheus 目标文件失败: {e}")
#                 target_list = []
#
#         # 2. 构建新的 targets (避免重复添加)
#         # 我们使用一个 set 来存储已有的 target，方便去重
#
#         new_targets = []
#         for ip in ip_list:
#             new_targets.append(f"{ip}:27684")
#
#         # 3. 如果有新节点，追加到列表中
#         if new_targets:
#             # 这里为了简单，将同一次导入的节点归为一个 job 或 group
#             # 你也可以选择将它们合并到已有的相同 labels 组中
#             target_list.append({
#                 "targets": new_targets,
#                 "labels": {
#                     "cluster": cluster_name,
#                     "source": "k8s_import",
#                     "env": "prod"
#                 }
#             })
#
#             try:
#                 with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
#                     json.dump(target_list, f, indent=4)
#                 print(f"[Prometheus] 已添加 {len(new_targets)} 个节点到监控目标文件。")
#             except Exception as e:
#                 logger.error(f"写入 Prometheus 目标文件失败: {e}")
#
#     @staticmethod
#     def query_metric(query):
#         """通用查询方法"""
#         try:
#             res = requests.get(PROMETHEUS_API_URL, params={'query': query}, timeout=5)
#             res_json = res.json()
#             if res_json['status'] == 'success' and res_json['data']['result']:
#                 return res_json['data']['result']
#         except Exception as e:
#             logger.error(f"Prometheus 查询失败 [{query}]: {e}")
#         return []
#
#     @staticmethod
#     def wait_for_data(ip_list, port=27684, max_retries=10, sleep_time=3):
#         print(f"正在等待监控数据就绪... (目标节点数: {len(ip_list)})")
#         for i in range(max_retries):
#             current_ready_count = 0
#             for ip in ip_list:
#                 # 构造查询语句，注意端口变量
#                 query = f'up{{instance="{ip}:{port}"}}'
#                 # 发起查询
#                 result = PrometheusHandler.query_metric(query)
#                 # 判断逻辑：有结果 且 value是1
#                 if result and len(result) > 0:
#                     value = result[0]['value'][1]  # Prometheus返回的是 [timestamp, "value"]
#                     if int(value) == 1:
#                         current_ready_count += 1
#             # 2. 本轮检查结束，判断是否全部就绪
#             if current_ready_count == len(ip_list):
#                 print("所有节点监控数据已就绪！")
#                 return True
#
#             # 3. 如果还没齐，打印进度并等待
#             print(f"[{i + 1}/{max_retries}] 等待中... 当前就绪: {current_ready_count}/{len(ip_list)}")
#             time.sleep(sleep_time)
#         print("等待超时，部分节点监控数据未就绪，请检查服务器Node-exporter是否正常部署")
#         return False
#
#     @staticmethod
#     def get_hardware_specs(ip):
#         """
#         查询 CPU, 内存, 磁盘
#         返回格式: {'cpu_cores': int, 'memory': str, 'disk_total': str}
#         """
#         instance = f"{ip}:27684"
#         specs = {}
#
#         # 1. CPU 核心数
#         # count(count(node_cpu_seconds_total{instance="..."}) by (cpu))
#         q_cpu = f'count(count(node_cpu_seconds_total{{instance="{instance}"}}) by (cpu))'
#         res_cpu = PrometheusHandler.query_metric(q_cpu)
#         specs['cpu_cores'] = int(res_cpu[0]['value'][1]) if res_cpu else 0
#
#         # 2. 内存 (转换成 GiB 字符串，保留2位小数)
#         # node_memory_MemTotal_bytes
#         q_mem = f'node_memory_MemTotal_bytes{{instance="{instance}"}}'
#         res_mem = PrometheusHandler.query_metric(q_mem)
#         if res_mem:
#             mem_gb = float(res_mem[0]['value'][1]) / 1024 / 1024 / 1024
#             specs['memory'] = f"{round(mem_gb, 2)} GiB"
#         else:
#             specs['memory'] = "0 GiB"
#
#         # 3. 磁盘总大小 (排除 docker/k8s 挂载，汇总物理磁盘)
#         # 逻辑：求和所有 ext4/xfs 文件系统的大小
#         q_disk = f'node_filesystem_size_bytes{{instance="{instance}", fstype=~"ext4|xfs|xfs_quota"}}'
#         res_disk = PrometheusHandler.query_metric(q_disk)
#
#         total_disk_gb = 0
#         if res_disk:
#             for item in res_disk:
#                 mountpoint = item['metric'].get('mountpoint', '')
#                 # 过滤掉容器产生的干扰挂载点
#                 if '/docker' in mountpoint or '/kubelet' in mountpoint or '/overlay' in mountpoint:
#                     continue
#                 total_disk_gb += float(item['value'][1])
#
#         # 转换为 GiB 或 TiB
#         disk_gb = total_disk_gb / 1024 / 1024 / 1024
#         if disk_gb > 1024:
#             specs['disk_total'] = f"{round(disk_gb / 1024, 2)} TiB"
#         else:
#             specs['disk_total'] = f"{round(disk_gb, 2)} GiB"
#
#         return specs


# --- 辅助函数：部署 Node Exporter DaemonSet (保持不变) ---
def check_and_deploy_node_exporter(api_client):
    app_api = client.AppsV1Api(api_client)
    core_api = client.CoreV1Api(api_client)
    namespace = "cmdb"
    name = "node-exporter"

    # 1. 确保 namespace
    try:
        core_api.read_namespace(name=namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            core_api.create_namespace(body=client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))

    # 2. 检查并创建 DaemonSet
    try:
        app_api.read_namespaced_daemon_set(name=name, namespace=namespace)
        print('有node-exporter了')
    except client.exceptions.ApiException as e:
        print('竟然没有node-exporter')
        if e.status == 404:
            # 简化版 manifest，生产环境建议放在 yaml 文件中读取
            manifest = {
                "apiVersion": "apps/v1",
                "kind": "DaemonSet",
                "metadata": {"name": name, "namespace": namespace, "labels": {"app": "node-exporter"}},
                "spec": {
                    "selector": {"matchLabels": {"app": "node-exporter"}},
                    "template": {
                        "metadata": {"labels": {"app": "node-exporter"}},
                        "spec": {
                            "hostNetwork": True, "hostPID": True,
                            "containers": [{
                                "name": "node-exporter",
                                "image": "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/quay.io/prometheus/node-exporter:v1.8.1",
                                "args": [
                                    "--path.rootfs=/host",
                                    "--web.listen-address=:27684",
                                    "--collector.tcpstat"
                                ],
                                "ports": [{"containerPort": 27684, "hostPort": 27684, "name": "metrics"}],
                                "volumeMounts": [{"name": "root", "mountPath": "/host", "readOnly": True}]
                            }],
                            "volumes": [{"name": "root", "hostPath": {"path": "/"}}],
                            "tolerations": [{"operator": "Exists"}]
                        }
                    }
                }
            }
            try:
                print('开始创建ds了')
                app_api.create_namespaced_daemon_set(namespace=namespace, body=manifest)
                return Response({"detail": "DaemonSet 创建成功"}, status=status.HTTP_201_CREATED)

            except ApiException as e:
                if e.status == 409:  # 已存在
                    return Response({"detail": "DaemonSet 已存在"}, status=status.HTTP_400_BAD_REQUEST)
                elif e.status == 403:  # 权限不足
                    return Response({"detail": "pod创建权限不足"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response(
                        {"detail": f"node_exportor创建失败: {e.reason}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )


# --- 核心逻辑修改：同步节点信息 ---
def sync_nodes_to_db_with_prom(api_client, cluster_instance, full_sync=True):
    v1 = client.CoreV1Api(api_client)
    try:
        # 1. 获取 K8s 节点列表 (快速失败配置)
        api_client.configuration.retries = 0
        k8s_nodes = v1.list_node(_request_timeout=(3, 5)).items

        total_nodes_count = len(k8s_nodes)
        print(f"[资源同步] K8s API 获取到 {total_nodes_count} 个节点")

        node_ip_map = {}
        all_ips = []

        # 2. 解析所有节点的 IP
        for node in k8s_nodes:
            ip_address = None
            for addr in node.status.addresses:
                if addr.type == "InternalIP":
                    ip_address = addr.address
                    break
            if not ip_address and node.status.addresses:
                ip_address = node.status.addresses[0].address

            if ip_address:
                node_ip_map[node.metadata.name] = ip_address
                all_ips.append(ip_address)

        # 3. (仅导入时) 更新 Prometheus 配置
        if full_sync:
            PrometheusHandler.update_target_file(all_ips, cluster_instance.name)
            if all_ips:
                PrometheusHandler.wait_for_data(all_ips, port=27684, max_retries=10, sleep_time=3)

        # --- 核心改变 1: 不再判断状态，对所有有 IP 的节点都发起并发查询 ---
        prom_data_result = {}
        nodes_to_query = [ip for ip in all_ips if ip]

        if nodes_to_query:
            # 只要有 IP，就去查，不管它是 Ready 还是 NotReady
            with ThreadPoolExecutor(max_workers=20) as executor:
                def fetch_metric(ip):
                    return ip, PrometheusHandler.get_hardware_specs(ip)

                future_to_ip = {executor.submit(fetch_metric, ip): ip for ip in nodes_to_query}

                for future in as_completed(future_to_ip):
                    try:
                        ip, specs = future.result(timeout=3)
                        # 只有成功拿到数据才放入结果字典
                        if specs:
                            prom_data_result[ip] = specs
                    except Exception:
                        # 查不到就查不到，后面会处理
                        pass

        # 初始化 NotReady 计数器
        not_ready_nodes_count = 0

        # 4. 循环写库
        for node in k8s_nodes:
            node_name = node.metadata.name
            ip_address = node_ip_map.get(node_name)

            # 安全 IP (防止数据库报错)
            safe_ip_address = ip_address if ip_address else ""

            # 解析基础信息
            labels = node.metadata.labels
            role = 'master' if (
                        'node-role.kubernetes.io/control-plane' in labels or 'node-role.kubernetes.io/master' in labels) else 'worker'
            os_image = node.status.node_info.os_image

            # K8s 状态判断
            status_str = 'Unknown'
            for cond in node.status.conditions:
                if cond.type == 'Ready':
                    status_str = 'Ready' if cond.status == 'True' else 'NotReady'
                    break

            if status_str != 'Ready':
                not_ready_nodes_count += 1

            # --- 核心改变 2: 数据写入逻辑 ---

            # 检查我们刚才是否成功抓到了 Prometheus 数据
            # 这里的逻辑是：只要 Prom 有数据，就用 Prom 的数据；否则才走兜底。

            has_prom_data = False
            specs = {}

            if ip_address and ip_address in prom_data_result:
                specs = prom_data_result[ip_address]
                # 简单校验一下数据有效性 (比如 cpu > 0)
                if specs.get('cpu_cores', 0) > 0:
                    has_prom_data = True

            if has_prom_data:
                # 【情况 A：Prometheus 有数据】(最理想情况)
                # 无论 K8s 状态是 Ready 还是 NotReady，只要拿到数据就更新进去！
                # 这样即使节点 NotReady，我们也能看到 CPU/内存信息。
                print(f"   -> 节点 {node_name} ({status_str})：获取到监控数据，执行全量更新。")
                Node.objects.update_or_create(
                    cluster=cluster_instance,
                    name=node_name,
                    defaults={
                        'ip_address': safe_ip_address,
                        'role': role,
                        'status': status_str,  # K8s 状态照实写
                        'cpu_cores': specs['cpu_cores'],
                        'memory': specs['memory'],
                        'disk_total': specs['disk_total'],
                        'os_image': os_image
                    }
                )
            else:
                # 【情况 B：Prometheus 没数据】(真·连不上了，或者新节点还没数据)
                # 这里依然保留之前的 "新旧节点区分逻辑" 以防止报错

                print(f"   -> 节点 {node_name} ({status_str})：无监控数据，执行兜底逻辑。")
                existing_node = Node.objects.filter(cluster=cluster_instance, name=node_name).first()

                if existing_node:
                    # 旧节点：只更新状态，保留历史数据
                    existing_node.status = status_str
                    existing_node.ip_address = safe_ip_address
                    existing_node.role = role
                    existing_node.os_image = os_image
                    existing_node.save()
                else:
                    # 新节点：必须插入，给默认值 0
                    Node.objects.create(
                        cluster=cluster_instance,
                        name=node_name,
                        ip_address=safe_ip_address,
                        role=role,
                        status=status_str,
                        os_image=os_image,
                        cpu_cores=0,
                        memory="0 GiB",
                        disk_total="0 GiB"
                    )

        # 5. 更新集群状态
        new_cluster_status = 'running'
        if total_nodes_count == 0:
            new_cluster_status = 'unknown'
        elif not_ready_nodes_count == 0:
            new_cluster_status = 'running'
        elif not_ready_nodes_count == total_nodes_count:
            new_cluster_status = 'unknown'
        else:
            new_cluster_status = 'abnormal'

        cluster_instance.cluster_status = new_cluster_status
        cluster_instance.save()

        return True

    except Exception as e:
        logger.error(f"同步节点失败: {e}")
        raise e


class NodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    只读接口：用于前端获取集群下的节点列表
    支持过滤: /api/nodes/?cluster=1
    """
    queryset = Node.objects.all()
    serializer_class = NodeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        cluster_id = self.request.query_params.get('cluster')
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
        return queryset


class ClusterViewSet(viewsets.ModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer

    def get_k8s_clients(self, cluster_instance):
        """根据数据库中的 kubeconfig 加载 api client"""
        config_dict = yaml.safe_load(cluster_instance.kubeconfig)
        client_configuration = client.Configuration()
        k8s_config.load_kube_config_from_dict(
            config_dict,
            client_configuration=client_configuration
        )
        api_client = client.ApiClient(configuration=client_configuration)
        return {
            'core': client.CoreV1Api(api_client),
            'apps': client.AppsV1Api(api_client),
            'batch': client.BatchV1Api(api_client),
            'net': client.NetworkingV1Api(api_client),
            'version': client.VersionApi(api_client)
        }

    # 获取仪表盘统计信息 ---
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """
        获取集群概览数据
        URL: GET /api/clusters/{id}/dashboard/?namespace=default
        """
        cluster = self.get_object()
        namespace = request.query_params.get('namespace', None)
        # 如果 namespace 为 'all' 或空字符串，视为查询所有
        if namespace == 'all' or not namespace:
            namespace = None

        try:
            apis = self.get_k8s_clients(cluster)

            # 1. 定义查询过滤参数
            # field_selector 用于 list_xxx 接口过滤字段
            list_opts = {}
            if namespace:
                list_opts['field_selector'] = f'metadata.namespace={namespace}'

            # 2. 获取基础信息 (Version & Uptime)
            # Uptime 计算：通常取 kube-system 命名空间的创建时间作为集群启动时间
            version = "Unknown"
            uptime_str = "-"
            try:
                version_info = apis['version'].get_code()
                version = version_info.git_version

                kube_system_ns = apis['core'].read_namespace("kube-system")
                creation_ts = kube_system_ns.metadata.creation_timestamp
                if creation_ts:
                    # 计算时长
                    delta = datetime.now(timezone.utc) - creation_ts
                    days = delta.days
                    hours = delta.seconds // 3600
                    mins = (delta.seconds % 3600) // 60
                    uptime_str = f"{days} days {hours} hours {mins} mins"
            except Exception as e:
                logger.warning(f"获取集群基础信息失败: {e}")

            # 3. 获取资源数量
            # 注意：Nodes, PVs, Namespaces 是集群级别的资源，不受 namespace 参数影响
            # 其他资源如果指定了 namespace，则只统计该 NS 下的数量

            def count_res(func, **kwargs):
                try:
                    return len(func(**kwargs).items)
                except:
                    return 0

            # 区分：带 namespace 过滤的 API 调用 和 全局 API 调用
            # 如果 namespace 存在，使用 list_namespaced_xxx；否则使用 list_xxx_for_all_namespaces
            # 为了代码简洁，这里做个简单的封装逻辑：

            # Helper: 根据是否有 namespace 决定调用哪个 API
            def get_count(api_instance, resource_name):
                method_name_all = f"list_{resource_name}_for_all_namespaces"
                method_name_ns = f"list_namespaced_{resource_name}"

                # 特殊资源：始终全局查询
                if resource_name in ['node', 'persistent_volume', 'namespace']:
                    return count_res(getattr(apis['core'], f"list_{resource_name}"))

                # 区分 Namespaced 资源
                if namespace:
                    method = getattr(api_instance, method_name_ns, None)
                    if method: return count_res(method, namespace=namespace)

                method = getattr(api_instance, method_name_all, None)
                if method: return count_res(method)
                return 0

            stats = {
                'nodes': get_count(apis['core'], 'node'),
                'namespaces': get_count(apis['core'], 'namespace'),
                'pvs': get_count(apis['core'], 'persistent_volume'),

                'pods': get_count(apis['core'], 'pod'),  # 额外加一个 Pod
                'services': get_count(apis['core'], 'service'),
                'config_maps': get_count(apis['core'], 'config_map'),
                'secrets': get_count(apis['core'], 'secret'),

                'deployments': get_count(apis['apps'], 'deployment'),
                'daemon_sets': get_count(apis['apps'], 'daemon_set'),
                'stateful_sets': get_count(apis['apps'], 'stateful_set'),

                'jobs': get_count(apis['batch'], 'job'),
                'cron_jobs': get_count(apis['batch'], 'cron_job'),

                'ingresses': count_res(apis['net'].list_namespaced_ingress,
                                       namespace=namespace) if namespace else count_res(
                    apis['net'].list_ingress_for_all_namespaces)
            }

            data = {
                "name": cluster.name,
                "version": version,
                "uptime": uptime_str,
                "stats": stats
            }
            return Response(data)

        except Exception as e:
            logger.error(f"Dashboard 数据获取失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def get_namespaces(self, request, pk=None):
        cluster = self.get_object()
        try:
            apis = self.get_k8s_clients(cluster)
            ns_list = apis['core'].list_namespace()

            data = [ns.metadata.name for ns in ns_list.items]

            return Response(data)

        except Exception as e:
            return Response({'detail': f'获取命名空间失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 新增接口 2：获取事件列表 ---
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """
        获取集群事件
        """
        cluster = self.get_object()
        namespace = request.query_params.get('namespace', None)
        apis = self.get_k8s_clients(cluster)

        try:
            apis = self.get_k8s_clients(cluster)
            if namespace and namespace != 'all':
                events = apis['core'].list_namespaced_event(namespace)
            else:
                events = apis['core'].list_event_for_all_namespaces()

            # 序列化
            data = []
            for e in events.items:
                # 优先使用 last_timestamp, 其次是 event_time
                t = e.last_timestamp or e.event_time or e.first_timestamp
                data.append({
                    "reason": e.reason,
                    "namespace": e.metadata.namespace,
                    "message": e.message,
                    "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                    "time": t
                })

            # 按时间倒序
            data.sort(key=lambda x: x['time'] if x['time'] else datetime.min, reverse=True)

            return Response(data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        try:
            # 1. 获取该集群关联的所有节点
            nodes = instance.nodes.all()

            targets_to_remove = []

            NODE_EXPORTER_PORT = 27684

            for node in nodes:
                if node.ip_address:
                    target = f"{node.ip_address}:{NODE_EXPORTER_PORT}"
                    targets_to_remove.append(target)

            # 2. 执行文件清理
            if targets_to_remove:
                print(f"正在删除集群 [{instance.name}] 的监控目标: {targets_to_remove}")
                PrometheusHandler.remove_targets_from_json(targets_to_remove)

        except Exception as e:
            print(f"清理 Prometheus 文件警告: {e}")

        # 3. 数据库删除
        super().perform_destroy(instance)

    def create(self, request, *args, **kwargs):
        data = request.data
        kubeconfig_str = data.get('kubeconfig')
        context_name = data.get('context')

        try:
            # 1. 加载 KubeConfig
            config_dict = yaml.safe_load(kubeconfig_str)
            client_configuration = client.Configuration()
            k8s_config.load_kube_config_from_dict(
                config_dict,
                context=context_name,
                client_configuration=client_configuration
            )
            api_client = client.ApiClient(configuration=client_configuration)

            # 2. 获取版本并保存 Cluster
            version_api = client.VersionApi(api_client)
            version_info = version_api.get_code()

            save_data = data.copy()
            save_data['version'] = version_info.git_version
            save_data['cluster_status'] = 'running'
            save_data['import_status'] = 'success'

            serializer = self.get_serializer(data=save_data)
            serializer.is_valid(raise_exception=True)
            cluster_instance = serializer.save()

            print(f"=== 开始处理集群 {cluster_instance.name} 的后续任务 ===")

            # 3. 部署 Node Exporter (核心改动: 先部署，确保有 agent)
            check_and_deploy_node_exporter(api_client)

            # 4. 同步节点信息 (核心改动: 包含注册 Prometheus 和查询逻辑)
            # 建议：如果是生产环境，这里应该用 Celery 异步执行，因为等待 Prometheus 抓取会阻塞 HTTP 请求
            sync_nodes_to_db_with_prom(api_client, cluster_instance, full_sync=True)

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.error(f"导入集群失败: {e}")
            return Response({"detail": f"处理失败: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=True, methods=['post'])
    # def sync_nodes(self, request, pk=None):
    #     # 1. 检查一下对象是否存在（可选，其实传 pk 给 celery 也可以）
    #     cluster = self.get_object()
    #
    #     # 2. 调用 Celery 任务 (使用 .delay)
    #     # 这一步是瞬间完成的，它只是把消息扔进 Redis
    #     task_sync_cluster_nodes.delay(cluster.id)
    #
    #     # 3. 直接返回成功
    #     return Response(
    #         {'detail': '同步任务已提交后台，请稍后刷新查看结果'},
    #         status=status.HTTP_200_OK
    #     )

    @action(detail=True, methods=['post'])
    def sync_nodes(self, request, pk=None):
        cluster = self.get_object()
        try:
            config_dict = yaml.safe_load(cluster.kubeconfig)
            client_configuration = client.Configuration()
            client_configuration.retries = 1
            k8s_config.load_kube_config_from_dict(
                config_dict,
                client_configuration=client_configuration
            )
            api_client = client.ApiClient(configuration=client_configuration)

            #使用线程池设置超时
            # 创建一个临时的线程池（只用一个线程）
            with ThreadPoolExecutor(max_workers=1) as executor:
                # 1. 提交任务到线程池
                future = executor.submit(sync_nodes_to_db_with_prom, api_client, cluster, full_sync=False)

                try:
                    # 2. 等待结果，最多等 5 秒
                    # 如果 sync_nodes_to_db_with_prom 有返回值，这里会拿到；没有则返回 None
                    future.result(timeout=7)

                except TimeoutError:
                    # 3. 捕获超时异常，直接返回 500
                    logger.error(f"集群 {cluster.name} 手动同步超时 (超过5秒)")


                    return Response({'detail': "同步失败: 操作超时，服务器响应时间超过5秒"},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'detail': '节点状态同步完成'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"手动同步失败: {e}")
            print('走到这里了')
            cluster.cluster_status = "unknown"
            cluster.save()
            cluster.nodes.update(status='NotReady')
            return Response({'detail': f"同步失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
