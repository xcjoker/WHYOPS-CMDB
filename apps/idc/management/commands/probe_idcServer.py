from django.core.management.base import BaseCommand
from apps.idc.models import IdcServer  # 注意这里根据你的目录结构可能需要调整，如 from idc.models import ...
import requests
import logging

# 配置项
PROMETHEUS_API_URL = "http://localhost:9090/api/v1/query"
CPU_THRESHOLD = 80.0
MEM_THRESHOLD = 80.0

# 状态映射
STATUS_ABNORMAL = 0
STATUS_FAULT = 1
STATUS_NORMAL = 2

# 设置日志
logger = logging.getLogger(__name__)


class PrometheusAgent:
    """
    Prometheus 查询代理类
    """

    def __init__(self, api_url):
        self.api_url = api_url

    def query_metric(self, query):
        try:
            response = requests.get(self.api_url, params={'query': query}, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data['status'] == 'success':
                return data['data']['result']
        except Exception as e:
            # 在 Django 命令中，建议使用 self.stderr 输出错误，或者使用 logger
            print(f"查询 Prometheus 失败: {query}, 错误: {e}")
        return []

    def get_server_metrics(self):
        metrics_map = {}

        # 1. 获取原始数据
        up_data = self.query_metric('up')
        cpu_data = self.query_metric('100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
        mem_data = self.query_metric('100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)')

        # 2. 辅助函数：提取IP
        def _extract_ip(instance_str):
            if not instance_str: return None
            return instance_str.split(':')[0]

        # 3. 处理数据
        for item in up_data:
            ip = _extract_ip(item['metric'].get('instance'))
            if ip:
                if ip not in metrics_map: metrics_map[ip] = {}
                metrics_map[ip]['up'] = float(item['value'][1])

        for item in cpu_data:
            ip = _extract_ip(item['metric'].get('instance'))
            if ip:
                if ip not in metrics_map: metrics_map[ip] = {}
                metrics_map[ip]['cpu'] = float(item['value'][1])

        for item in mem_data:
            ip = _extract_ip(item['metric'].get('instance'))
            if ip:
                if ip not in metrics_map: metrics_map[ip] = {}
                metrics_map[ip]['mem'] = float(item['value'][1])

        return metrics_map


# --- 核心修改：必须包含 Command 类 ---
class Command(BaseCommand):
    help = '探测 IDC 服务器状态并更新数据库'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始执行 IDC 服务器巡检...'))

        agent = PrometheusAgent(PROMETHEUS_API_URL)

        # 1. 获取数据
        metrics_data = agent.get_server_metrics()

        # 2. 查询数据库
        servers = IdcServer.objects.all()
        updates_count = 0

        for server in servers:
            target_ip = server.ip
            server_metric = metrics_data.get(target_ip)

            new_status = STATUS_NORMAL
            reason = "正常"

            if not server_metric:
                new_status = STATUS_FAULT
                reason = "监控数据缺失"
            else:
                is_up = server_metric.get('up', 0)
                cpu = server_metric.get('cpu', 0)
                mem = server_metric.get('mem', 0)

                if is_up == 0:
                    new_status = STATUS_FAULT
                    reason = "Node Exporter 离线"
                elif cpu > CPU_THRESHOLD or mem > MEM_THRESHOLD:
                    new_status = STATUS_ABNORMAL
                    reason = f"资源超标 (CPU:{cpu:.1f}%, MEM:{mem:.1f}%)"

            # 状态变更时更新数据库
            if server.scan_status != new_status:
                old_status = server.get_scan_status_display()
                server.scan_status = new_status
                server.save()
                updates_count += 1

                # 使用 Django 专门的输出方式
                self.stdout.write(self.style.WARNING(f"[{server.ip}] 状态变更: {old_status} -> {reason}"))

        self.stdout.write(self.style.SUCCESS(f'巡检结束。扫描服务器: {len(servers)} 台，更新状态: {updates_count} 台。'))