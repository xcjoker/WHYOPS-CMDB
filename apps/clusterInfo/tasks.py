# apps/clusterInfo/tasks.py
from celery import shared_task
from .models import Cluster
from kubernetes import client, config as k8s_config
import yaml
import logging
from .utils import sync_nodes_to_db_with_prom

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def task_sync_cluster_nodes(self, cluster_id):
    """
    Celery 异步任务：同步集群节点
    """
    try:
        logger.info(f"Celery 开始同步集群 {cluster_id}")

        # 1. 在 Worker 进程中重新获取 Cluster 对象
        cluster = Cluster.objects.get(id=cluster_id)

        # 2. 重新建立 K8s 连接 (这是必须的，因为 Socket 不能跨进程传递)
        config_dict = yaml.safe_load(cluster.kubeconfig)
        client_configuration = client.Configuration()
        client_configuration.retries = 0  # 依然建议关闭自动重试

        k8s_config.load_kube_config_from_dict(
            config_dict,
            client_configuration=client_configuration
        )
        api_client = client.ApiClient(configuration=client_configuration)

        # 3. 调用核心同步逻辑
        # 注意：这里的 full_sync=False，且 sync_nodes_to_db_with_prom 内部
        # 依然建议保留 _request_timeout=(2, 5) 来防止 Worker 卡死
        sync_nodes_to_db_with_prom(api_client, cluster, full_sync=False)

        logger.info(f"集群 {cluster.name} 同步完成")
        return f"Cluster {cluster.name} synced"

    except Cluster.DoesNotExist:
        logger.error(f"集群ID {cluster_id} 不存在")
    except Exception as e:
        logger.error(f"同步任务失败: {e}")
        # 可选：抛出异常让 Celery 重试，或者直接记录失败
        raise self.retry(exc=e, countdown=5)