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
        client_configuration.retries = 0
        api_client = client.ApiClient(configuration=client_configuration)

        try:
            client.VersionApi(api_client).get_code(_request_timeout=3)
        except Exception as e:
            logger.error(f"Cluster {cluster_id} connection timed out: {e}")
            raise Exception("集群连接超时 (3s) 或不可达")

        # 动态加载 Ingress 旧版 API (防止新版 Python 库报错)
        BetaNetClass = getattr(client, "NetworkingV1beta1Api", None)
        net_beta = BetaNetClass(api_client) if BetaNetClass else None

        return {
            'core': client.CoreV1Api(api_client),             # Service 需要
            'net_v1': client.NetworkingV1Api(api_client),     # Ingress (新版 k8s >= 1.19)
            'net_beta': net_beta                              # Ingress (旧版 k8s < 1.19)
        }
    except Cluster.DoesNotExist:
        raise Exception(f"ID为 {cluster_id} 的集群不存在")
    except Exception as e:
        raise Exception(f"K8s连接失败: {str(e)}")


class ServiceViewSet(viewsets.ViewSet):
    def list(self, request):
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')

        if not cluster_id:
            return Response({"detail": "缺少 cluster_id 参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apis = get_k8s_clients(cluster_id)
            core_api = apis['core']

            # 获取列表
            if namespace == 'all':
                svc_list = core_api.list_service_for_all_namespaces(_request_timeout=10)
            else:
                svc_list = core_api.list_namespaced_service(namespace, _request_timeout=10)

            data = []
            for svc in svc_list.items:
                # 1. 基础信息
                name = svc.metadata.name
                ns = svc.metadata.namespace
                svc_type = svc.spec.type
                cluster_ip = svc.spec.cluster_ip

                # 2. 外部 IP 处理
                external_ips = []

                # 情况A: LoadBalancer 自动分配的 IP
                if svc.status.load_balancer and svc.status.load_balancer.ingress:
                    for ingress in svc.status.load_balancer.ingress:
                        if ingress.ip: external_ips.append(ingress.ip)
                        if ingress.hostname: external_ips.append(ingress.hostname)

                # 情况B: 手动指定的 externalIPs
                # 【修复点】这里属性名必须是 external_i_ps
                if svc.spec.external_i_ps:
                    external_ips.extend(svc.spec.external_i_ps)

                # 3. 端口处理
                ports = []
                if svc.spec.ports:
                    for p in svc.spec.ports:
                        port_str = f"{p.port}"
                        if p.node_port:
                            port_str += f":{p.node_port}"
                        port_str += f"/{p.protocol}"
                        ports.append(port_str)

                # 4. Selector 处理
                selector = svc.spec.selector or {}
                selector_str = [f"{k}={v}" for k, v in selector.items()]

                # 5. Age
                age = "Unknown"
                if svc.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - svc.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                data.append({
                    "name": name,
                    "namespace": ns,
                    "type": svc_type,
                    "cluster_ip": cluster_ip,
                    "external_ips": external_ips,
                    "ports": ports,
                    "selector": selector_str,
                    "age": age,
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 Service 列表失败: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """创建 Service"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            svc_data = yaml.safe_load(yaml_content)
            namespace = svc_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)
            apis['core'].create_namespaced_service(namespace, svc_data)

            return Response({"detail": "创建指令已发送"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """删除 Service"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            apis['core'].delete_namespaced_service(name, namespace)
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
                obj = core_api.read_namespaced_service(name, namespace)
                data_dict = core_api.api_client.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                core_api.replace_namespaced_service(name, namespace, body)
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IngressViewSet(viewsets.ViewSet):
    def _parse_rules(self, rules, is_v1):
        """辅助函数：统一解析 Ingress 规则 (屏蔽 v1 和 beta1 的差异)"""
        if not rules:
            return []

        parsed_rules = []
        for rule in rules:
            host = rule.host or "*"
            paths_list = []

            if rule.http and rule.http.paths:
                for p in rule.http.paths:
                    path_str = p.path or "/"

                    # === 差异处理核心 ===
                    svc_name = "Unknown"
                    svc_port = "Unknown"

                    if is_v1:
                        # v1: backend -> service -> name/port
                        if p.backend and p.backend.service:
                            svc_name = p.backend.service.name
                            # port 可能是 number 或 name
                            if p.backend.service.port:
                                svc_port = p.backend.service.port.number or p.backend.service.port.name
                    else:
                        # v1beta1: backend -> service_name/service_port
                        if p.backend:
                            svc_name = getattr(p.backend, 'service_name', 'Unknown')
                            svc_port = getattr(p.backend, 'service_port', 'Unknown')

                    paths_list.append({
                        "path": path_str,
                        "backend": f"{svc_name}:{svc_port}"
                    })

            parsed_rules.append({
                "host": host,
                "paths": paths_list
            })
        return parsed_rules

    def list(self, request):
        """获取 Ingress 列表 (自动降级兼容)"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        if not cluster_id:
            return Response({"detail": "缺少 cluster_id"}, status=400)

        try:
            apis = get_k8s_clients(cluster_id)
            net_v1 = apis['net_v1']
            net_beta = apis['net_beta']

            ing_items = []
            is_v1_api = True  # 标记当前使用的是否为 V1

            # 1. 尝试使用 NetworkingV1 (首选)
            try:
                if namespace == 'all':
                    res = net_v1.list_ingress_for_all_namespaces(_request_timeout=10)
                else:
                    res = net_v1.list_namespaced_ingress(namespace, _request_timeout=10)
                ing_items = res.items
            except Exception as e:
                # 2. 如果 V1 失败 (如 404 Not Found)，且 Beta 客户端存在，尝试降级
                if net_beta:
                    try:
                        is_v1_api = False  # 标记为旧版
                        if namespace == 'all':
                            res = net_beta.list_ingress_for_all_namespaces(_request_timeout=10)
                        else:
                            res = net_beta.list_namespaced_ingress(namespace, _request_timeout=10)
                        ing_items = res.items
                    except Exception as e2:
                        raise e  # 两次都失败，抛出异常
                else:
                    raise e  # 没有 Beta 客户端，直接抛出

            # 3. 数据格式化
            data = []
            for ing in ing_items:
                # 基础信息
                name = ing.metadata.name
                ns = ing.metadata.namespace

                # Ingress Class
                # v1 在 spec.ingress_class_name, v1beta1 在 annotations
                ing_class = getattr(ing.spec, 'ingress_class_name', None)
                if not ing_class and ing.metadata.annotations:
                    ing_class = ing.metadata.annotations.get('kubernetes.io/ingress.class', '')

                # LoadBalancer Address
                addresses = []
                if ing.status.load_balancer and ing.status.load_balancer.ingress:
                    for lb in ing.status.load_balancer.ingress:
                        if lb.ip: addresses.append(lb.ip)
                        if lb.hostname: addresses.append(lb.hostname)

                # 规则解析 (传入版本标记)
                rules_data = self._parse_rules(ing.spec.rules, is_v1_api)

                # Age
                age = "Unknown"
                if ing.metadata.creation_timestamp:
                    delta = datetime.now(timezone.utc) - ing.metadata.creation_timestamp
                    if delta.days > 0:
                        age = f"{delta.days}d"
                    else:
                        age = f"{delta.seconds // 3600}h"

                data.append({
                    "name": name,
                    "namespace": ns,
                    "class": ing_class,
                    "addresses": addresses,
                    "rules": rules_data,
                    "age": age,
                    "api_version": "v1" if is_v1_api else "v1beta1"  # 方便调试
                })

            return Response(data)

        except Exception as e:
            logger.error(f"获取 Ingress 失败: {e}")
            return Response({"detail": str(e)}, status=500)

    def create(self, request):
        """创建 Ingress"""
        cluster_id = request.data.get('cluster_id')
        yaml_content = request.data.get('yaml')
        if not cluster_id or not yaml_content:
            return Response({"detail": "缺少参数"}, status=400)

        try:
            yaml_content = yaml_content.replace('\t', '  ')
            ing_data = yaml.safe_load(yaml_content)
            namespace = ing_data.get('metadata', {}).get('namespace', 'default')

            apis = get_k8s_clients(cluster_id)

            # 根据 YAML 的 apiVersion 决定调用哪个接口，或者直接尝试
            api_version = ing_data.get('apiVersion', 'networking.k8s.io/v1')

            if 'v1beta1' in api_version and apis['net_beta']:
                apis['net_beta'].create_namespaced_ingress(namespace, ing_data)
            else:
                apis['net_v1'].create_namespaced_ingress(namespace, ing_data)

            return Response({"detail": "创建指令已发送"}, status=201)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    def destroy(self, request, pk=None):
        """删除 Ingress"""
        cluster_id = request.query_params.get('cluster_id')
        namespace = request.query_params.get('namespace', 'default')
        name = pk
        try:
            apis = get_k8s_clients(cluster_id)
            # 优先尝试 v1 删除，失败尝试 beta
            try:
                apis['net_v1'].delete_namespaced_ingress(name, namespace)
            except Exception:
                if apis['net_beta']:
                    apis['net_beta'].delete_namespaced_ingress(name, namespace)
                else:
                    raise
            return Response(status=204)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)

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
            net_v1 = apis['net_v1']
            net_beta = apis['net_beta']

            if request.method == 'GET':
                try:
                    obj = net_v1.read_namespaced_ingress(name, namespace)
                    client_api = net_v1.api_client
                except:
                    if net_beta:
                        obj = net_beta.read_namespaced_ingress(name, namespace)
                        client_api = net_beta.api_client
                    else:
                        raise

                data_dict = client_api.sanitize_for_serialization(obj)
                if 'metadata' in data_dict and 'managedFields' in data_dict['metadata']:
                    del data_dict['metadata']['managedFields']
                return Response({'content': yaml.safe_dump(data_dict, default_flow_style=False)})

            elif request.method == 'PUT':
                content = request.data.get('content')
                body = yaml.safe_load(content)
                # 简单粗暴：优先尝试 V1 更新
                try:
                    net_v1.replace_namespaced_ingress(name, namespace, body)
                except:
                    if net_beta:
                        net_beta.replace_namespaced_ingress(name, namespace, body)
                    else:
                        raise
                return Response({'detail': '更新成功'})

        except Exception as e:
            return Response({"detail": str(e)}, status=500)
