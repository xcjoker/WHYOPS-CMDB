from kubernetes import client
from .models import Node
from .PrometheusHandler import PrometheusHandler, logger
from concurrent.futures import ThreadPoolExecutor, as_completed


def sync_nodes_to_db_with_prom(api_client, cluster_instance, full_sync=True):
    v1 = client.CoreV1Api(api_client)
    try:
        # --- 优化 1: K8s API 设置连接和读取超时 ---
        # 连接超时 2秒，读取超时 5秒
        k8s_nodes = v1.list_node(_request_timeout=(3, 5)).items
        print(f"[资源同步] K8s API 获取到 {len(k8s_nodes)} 个节点")

        node_ip_map = {}
        all_ips = []

        # 1. 解析 IP 映射关系 (纯内存操作，很快)
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

        # 2. 处理 Prometheus 配置更新 (仅导入模式)
        if full_sync:
            PrometheusHandler.update_target_file(all_ips, cluster_instance.name)
            print("[资源同步] 等待 Node Exporter 就绪及 Prometheus 抓取...")
            if all_ips:
                # 注意：这里的 wait_for_data 可能会运行 30秒 (10次 * 3秒)
                # 如果你在 View 层设置了 5秒超时，这里会导致导入失败。
                # 建议：导入时不要在 View 层加 5秒限制，或者手动同步时传入 full_sync=False
                is_ready = PrometheusHandler.wait_for_data(all_ips, port=27684, max_retries=10, sleep_time=3)
                if not is_ready:
                    print("[Warning] Prometheus 尚未抓取到数据")

        # --- 优化 2: 并发获取所有节点的 Prometheus 数据 ---
        # 准备一个字典来存结果: { '192.168.1.10': {'cpu_cores': 4, ...}, ... }
        prom_data_result = {}

        # 只有在非 full_sync (手动同步) 或者 full_sync 且数据就绪时才查询
        # 如果是手动同步，我们希望速度极快，所以必须并发
        nodes_to_query = [ip for ip in all_ips if ip]

        if nodes_to_query:
            # 使用线程池并发查询，而不是在下面的 for 循环里串行查询
            # max_workers=20 意味着同时查 20 个节点
            with ThreadPoolExecutor(max_workers=20) as executor:
                # 定义一个临时任务函数
                def fetch_metric(ip):
                    return ip, PrometheusHandler.get_hardware_specs(ip)

                # 提交任务
                future_to_ip = {executor.submit(fetch_metric, ip): ip for ip in nodes_to_query}

                for future in as_completed(future_to_ip):
                    try:
                        # 获取单个节点的查询结果，设置单次查询超时 3秒
                        ip, specs = future.result(timeout=3)
                        prom_data_result[ip] = specs
                    except Exception as e:
                        print(f"   [Warning] 获取节点指标失败: {e}")
                        # 失败了就不存入字典，后面会用默认值 0

        # 3. 循环写数据库 (数据库写操作通常很快，不需要并发，避免死锁)
        for node in k8s_nodes:
            node_name = node.metadata.name
            ip_address = node_ip_map.get(node_name)

            # --- K8s 基础信息 ---
            labels = node.metadata.labels
            role = 'master' if (
                    'node-role.kubernetes.io/control-plane' in labels or 'node-role.kubernetes.io/master' in labels) else 'worker'
            os_image = node.status.node_info.os_image

            # 判断 K8s 状态
            status_str = 'Unknown'
            for cond in node.status.conditions:
                if cond.type == 'Ready':
                    status_str = 'Ready' if cond.status == 'True' else 'NotReady'
                    break

            # 如果节点不是 Ready 且不是全量同步，跳过硬件更新
            if not full_sync and status_str != 'Ready':
                print(f"   -> 节点 {node_name} 状态为 {status_str}，跳过 Prometheus 查询。")
                Node.objects.update_or_create(
                    cluster=cluster_instance,
                    name=node_name,
                    defaults={'status': status_str}
                )
                continue

            # --- 获取硬件信息 ---
            # 直接从刚才并发查询的结果字典里拿，耗时为 0
            cpu_cores = 0
            memory_str = "0 GiB"
            disk_str = "0 GiB"

            if ip_address and ip_address in prom_data_result:
                specs = prom_data_result[ip_address]
                if specs.get('cpu_cores', 0) > 0:
                    cpu_cores = specs['cpu_cores']
                    memory_str = specs['memory']
                    disk_str = specs['disk_total']

            # 写库
            Node.objects.update_or_create(
                cluster=cluster_instance,
                name=node_name,
                defaults={
                    'ip_address': ip_address,
                    'role': role,
                    'status': status_str,
                    'cpu_cores': cpu_cores,
                    'disk_total': disk_str,
                    'memory': memory_str,
                    'os_image': os_image
                }
            )
        return True

    except Exception as e:
        logger.error(f"同步节点失败: {e}")
        # 这里不需要 raise e，因为外层的 View 里的 ThreadPoolExecutor 会捕获到异常
        # 但为了让外层知道出错了，raise 也是可以的
        raise e
