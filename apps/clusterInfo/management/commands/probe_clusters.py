# app/management/commands/probe_clusters.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.clusterInfo.models import Cluster
from kubernetes import client, config
import yaml
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '多线程探测所有 Kubernetes 集群的在线状态'

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"[{start_time}] 开始执行集群健康检查...")

        # 获取所有需要探测的集群
        clusters = Cluster.objects.all()
        total_count = clusters.count()

        if total_count == 0:
            self.stdout.write("没有集群需要探测。")
            return

        # 结果统计
        results = {'running': 0, 'abnormal': 0, 'unknown': 0}

        # 使用线程池并发探测
        # max_workers 可以根据你的服务器性能调整，一般 10-20 比较合适
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_cluster = {}

            # 2. 遍历每一个集群
            for cluster in clusters:
                # 3. 提交任务给线程池，它会立即返回一个 future 对象（相当于一个任务句柄或凭证）
                future = executor.submit(self.check_single_cluster, cluster)
                future_to_cluster[future] = cluster

            # 处理完成的任务
            for future in as_completed(future_to_cluster):
                cluster = future_to_cluster[future]
                try:
                    status_code = future.result()
                    results[status_code] += 1
                except Exception as exc:
                    logger.error(f"探测任务执行异常: {cluster.name} - {exc}")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        self.stdout.write(self.style.SUCCESS(
            f"探测结束。耗时: {duration:.2f}s | "
            f"就绪: {results['running']} | 异常: {results['abnormal']}"
        ))

    def check_single_cluster(self, cluster_obj):
        """
        探测单个集群逻辑 (在子线程中运行)
        返回: 'running' | 'abnormal'
        """
        original_status = cluster_obj.cluster_status
        new_status = 'unknown'

        try:
            # 1. 解析 kubeconfig
            # 你的 models.py 中 kubeconfig 是 TextField
            kubeconfig_dict = yaml.safe_load(cluster_obj.kubeconfig)

            # 2. 创建独立的配置对象 (线程安全关键)
            client_conf = client.Configuration()
            config.load_kube_config_from_dict(
                kubeconfig_dict,
                client_configuration=client_conf
            )

            # 3. 关键设置：超时时间
            # 连接超时 2秒，读取超时 3秒，总共最多 5秒
            client_conf.retries = 0

            # 4. 发起请求
            api_client = client.ApiClient(configuration=client_conf)
            core_api = client.CoreV1Api(api_client)

            # 尝试列出 default 命名空间（极轻量）
            core_api.list_namespace(limit=1, _request_timeout=(2, 3))

            # 如果没报错，就是成功
            new_status = 'running'

        except Exception as e:
            # 记录详细错误日志以便排查
            # logger.warning(f"集群 {cluster_obj.name} 离线: {str(e)}")
            new_status = 'abnormal'

        # 5. 只有状态发生变化时才写入数据库，减少 DB 锁竞争
        if new_status != original_status:
            # 注意：在多线程环境下使用 Django ORM 更新单个对象通常是安全的
            # 但为了保险，只更新特定字段
            cluster_obj.cluster_status = new_status
            cluster_obj.save(update_fields=['cluster_status'])
            print(f"状态更新: {cluster_obj.name} -> {new_status}")

        return new_status