import json
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

SOFT_DIR = r'D:\pycharm\oaback\apps\idc\soft'
JSON_FILE_PATH = os.path.join(SOFT_DIR, 'node_exporter_targets.json')
# Prometheus API 地址
PROMETHEUS_API_URL = "http://localhost:9090/api/v1/query"

class PrometheusHandler:
    """
    处理与 Prometheus 相关的操作：文件注册、查询
    """
    @staticmethod
    def remove_targets_from_json(targets_to_remove):
        if not targets_to_remove or not os.path.exists(JSON_FILE_PATH):
            return

        try:
            # 1. 读取文件
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)  # data 是一个列表List [ {}, {}, {} ]

            if not data:
                return

            original_count = 0

            for job_group in data:
                current_targets = job_group.get('targets', [])
                original_count += len(current_targets)

                job_group['targets'] = [t for t in current_targets if t not in targets_to_remove]

            data = [group for group in data if len(group.get('targets', [])) > 0]

            # 4. 写回文件
            with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                # ensure_ascii=False 保证中文字符（如"集群一"）正常显示，不转义成 \uXXXX
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"Prometheus 目标清理完成。需移除: {targets_to_remove}")

        except Exception as e:
            print(f"移除 Prometheus 目标失败: {e}")

    @staticmethod
    def update_target_file(ip_list, cluster_name):
        """
        批量将 IP 列表写入 JSON 文件
        """
        if not ip_list:
            return

        # 1. 读取现有文件
        target_list = []
        if os.path.exists(JSON_FILE_PATH):
            try:
                with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        target_list = json.loads(content)
            except Exception as e:
                logger.error(f"读取 Prometheus 目标文件失败: {e}")
                target_list = []

        # 2. 构建新的 targets (避免重复添加)
        # 我们使用一个 set 来存储已有的 target，方便去重

        new_targets = []
        for ip in ip_list:
            new_targets.append(f"{ip}:27684")

        # 3. 如果有新节点，追加到列表中
        if new_targets:
            # 这里为了简单，将同一次导入的节点归为一个 job 或 group
            # 你也可以选择将它们合并到已有的相同 labels 组中
            target_list.append({
                "targets": new_targets,
                "labels": {
                    "cluster": cluster_name,
                    "source": "k8s_import",
                    "env": "prod"
                }
            })

            try:
                with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(target_list, f, indent=4)
                print(f"[Prometheus] 已添加 {len(new_targets)} 个节点到监控目标文件。")
            except Exception as e:
                logger.error(f"写入 Prometheus 目标文件失败: {e}")

    @staticmethod
    def query_metric(query):
        """通用查询方法"""
        try:
            res = requests.get(PROMETHEUS_API_URL, params={'query': query}, timeout=5)
            res_json = res.json()
            if res_json['status'] == 'success' and res_json['data']['result']:
                return res_json['data']['result']
        except Exception as e:
            logger.error(f"Prometheus 查询失败 [{query}]: {e}")
        return []

    @staticmethod
    def wait_for_data(ip_list, port=27684, max_retries=10, sleep_time=3):
        print(f"正在等待监控数据就绪... (目标节点数: {len(ip_list)})")
        for i in range(max_retries):
            current_ready_count = 0
            for ip in ip_list:
                # 构造查询语句，注意端口变量
                query = f'up{{instance="{ip}:{port}"}}'
                # 发起查询
                result = PrometheusHandler.query_metric(query)
                # 判断逻辑：有结果 且 value是1
                if result and len(result) > 0:
                    value = result[0]['value'][1]  # Prometheus返回的是 [timestamp, "value"]
                    if int(value) == 1:
                        current_ready_count += 1
            # 2. 本轮检查结束，判断是否全部就绪
            if current_ready_count == len(ip_list):
                print("所有节点监控数据已就绪！")
                return True

            # 3. 如果还没齐，打印进度并等待
            print(f"[{i + 1}/{max_retries}] 等待中... 当前就绪: {current_ready_count}/{len(ip_list)}")
            time.sleep(sleep_time)
        print("等待超时，部分节点监控数据未就绪，请检查服务器Node-exporter是否正常部署")
        return False

    @staticmethod
    def get_hardware_specs(ip):
        """
        查询 CPU, 内存, 磁盘
        返回格式: {'cpu_cores': int, 'memory': str, 'disk_total': str}
        """
        instance = f"{ip}:27684"
        specs = {}

        # 1. CPU 核心数
        # count(count(node_cpu_seconds_total{instance="..."}) by (cpu))
        q_cpu = f'count(count(node_cpu_seconds_total{{instance="{instance}"}}) by (cpu))'
        res_cpu = PrometheusHandler.query_metric(q_cpu)
        specs['cpu_cores'] = int(res_cpu[0]['value'][1]) if res_cpu else 0

        # 2. 内存 (转换成 GiB 字符串，保留2位小数)
        # node_memory_MemTotal_bytes
        q_mem = f'node_memory_MemTotal_bytes{{instance="{instance}"}}'
        res_mem = PrometheusHandler.query_metric(q_mem)
        if res_mem:
            mem_gb = float(res_mem[0]['value'][1]) / 1024 / 1024 / 1024
            specs['memory'] = f"{round(mem_gb, 2)} GiB"
        else:
            specs['memory'] = "0 GiB"

        # 3. 磁盘总大小 (排除 docker/k8s 挂载，汇总物理磁盘)
        # 逻辑：求和所有 ext4/xfs 文件系统的大小
        q_disk = f'node_filesystem_size_bytes{{instance="{instance}", fstype=~"ext4|xfs|xfs_quota"}}'
        res_disk = PrometheusHandler.query_metric(q_disk)

        total_disk_gb = 0
        if res_disk:
            for item in res_disk:
                mountpoint = item['metric'].get('mountpoint', '')
                # 过滤掉容器产生的干扰挂载点
                if '/docker' in mountpoint or '/kubelet' in mountpoint or '/overlay' in mountpoint:
                    continue
                total_disk_gb += float(item['value'][1])

        # 转换为 GiB 或 TiB
        disk_gb = total_disk_gb / 1024 / 1024 / 1024
        if disk_gb > 1024:
            specs['disk_total'] = f"{round(disk_gb / 1024, 2)} TiB"
        else:
            specs['disk_total'] = f"{round(disk_gb, 2)} GiB"

        return specs