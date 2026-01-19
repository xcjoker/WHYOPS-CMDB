import json
import math
import os
import time

from rest_framework import viewsets, status, generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.idc.models import IdcRegion, IdcServer
from .serializer import IdcRegionSerializer, GetIdcServerSerializer, IdcServerUpdateSerializer, IdcServerSerializer
import paramiko
import requests
import math
from datetime import datetime

GLOBAL_FUNCTION = ''  # 也可以不在这里定义，只是为了让人更清楚地看到全局变量
GLOBAL_REGION = None
SOFT_DIR = r'D:\pycharm\oaback\apps\idc\soft'
# 【注意】请修改为你实际下载的文件名
NODE_PKG_NAME = 'node_exporter-1.6.1.linux-amd64.tar.gz'
JSON_FILE_PATH = os.path.join(SOFT_DIR, 'node_exporter_targets.json')
PROMETHEUS_API_URL = "http://localhost:9090/api/v1/query"
CMDB_API_URL = "http://192.168.239.1:8000/idc/server/api/"


class IdcRegionView(viewsets.ModelViewSet):
    queryset = IdcRegion.objects.all()
    serializer_class = IdcRegionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)  # 返回成功响应
        else:
            detail = list(serializer.errors.values())[0][0]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)  # 返回400错误


class IdcServerView(APIView):
    def post(self, request):
        global GLOBAL_FUNCTION
        global GLOBAL_REGION

        # ---------------------------------------------------------
        # 1. 基础校验
        # ---------------------------------------------------------
        serializer = IdcServerSerializer(data=request.data)
        if not serializer.is_valid():
            print("校验失败具体原因:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        ip = validated_data['ip']
        password = validated_data['password']
        GLOBAL_FUNCTION = validated_data['function']
        address = validated_data['region']

        GLOBAL_REGION = IdcRegion.objects.filter(address=address).first()
        if not GLOBAL_REGION:
            return Response({'detail': '地域不存在'}, status=status.HTTP_400_BAD_REQUEST)

        # ---------------------------------------------------------
        # 2. SSH 部署 Node Exporter (保持你原有逻辑)
        # ---------------------------------------------------------
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            try:
                ssh.connect(hostname=ip, username='root', password=password, timeout=10)
            except Exception as e:
                return Response({'detail': f'SSH连接失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

            sftp = ssh.open_sftp()
            local_path = os.path.join(SOFT_DIR, NODE_PKG_NAME)
            remote_path = f'/tmp/{NODE_PKG_NAME}'

            try:
                sftp.put(local_path, remote_path)
                # 直接写入服务文件，防止缩进问题
                service_content = """[Unit]
    Description=Node Exporter
    After=network.target

    [Service]
    User=node_exporter
    Group=node_exporter
    Type=simple
    ExecStart=/usr/local/bin/node_exporter --collector.tcpstat --web.listen-address=:27683

    [Install]
    WantedBy=multi-user.target
    """
                with sftp.open('/etc/systemd/system/node_exporter.service', 'w') as f:
                    f.write(service_content)
            except Exception as e:
                return Response({'detail': f'文件上传/写入失败: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                sftp.close()

            # 安装命令
            install_cmd = f"""
                    tar -xvf {remote_path} -C /tmp/ &&
                    mv /tmp/node_exporter-*/node_exporter /usr/local/bin/ &&
                    useradd -rs /bin/false node_exporter || true &&
                    systemctl daemon-reload &&
                    systemctl enable node_exporter &&
                    systemctl restart node_exporter
                """
            stdin, stdout, stderr = ssh.exec_command(install_cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                err_msg = stderr.read().decode()
                return Response({'detail': f'部署失败: {err_msg}'}, status=status.HTTP_400_BAD_REQUEST)

            # ---------------------------------------------------------
            # 3. 更新 Prometheus 发现文件
            # ---------------------------------------------------------
            self.update_prometheus_target(ip, address)

        except Exception as e:
            return Response({'detail': f'部署过程错误: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            ssh.close()

        # ---------------------------------------------------------
        # 4. 【新增】从 Prometheus 获取数据并 POST 到 CMDB
        # ---------------------------------------------------------
        try:
            # 4.1 等待数据就绪 (轮询)
            print(f"[*] 正在等待 Prometheus 抓取 {ip} 的数据...")
            instance_name = f"{ip}:27683"
            if not self.wait_for_prometheus_data(instance_name):
                return Response({'detail': '部署成功，但Prometheus抓取超时，请稍后手动同步'},
                                status=status.HTTP_201_CREATED)

            # 4.2 查询并格式化数据
            print(f"[*] 开始从 Prometheus 获取 {ip} 详细信息")
            server_info = self.collect_server_info_from_prom(ip, instance_name)
            print(server_info)

            # 4.3 发送 POST 请求
            print(f"[*] 正在上报数据到: {CMDB_API_URL}")
            # 注意：info_get.py 里是 data=json.dumps(getdata)，requests 默认 Content-Type 不是 json
            headers = {'Content-Type': 'application/json'}
            res = requests.post(CMDB_API_URL, data=json.dumps(server_info), headers=headers)

            if res.status_code not in [200, 201]:
                return Response({'detail': '部署成功，但CMDB上报失败'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"[-] 信息同步阶段出错: {e}")
            # 即使同步失败，部署也是成功的，所以返回 201，但在 detail 里提示
            return Response({'detail': f'部署成功，但信息同步出错: {str(e)}'}, status=status.HTTP_201_CREATED)

        return Response({'detail': '部署成功并已完成信息同步'}, status=status.HTTP_200_OK)

    # ================= 辅助方法 =================

    def update_prometheus_target(self, ip, region):
        """更新 JSON 文件"""
        target_list = []
        if os.path.exists(JSON_FILE_PATH):
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    target_list = json.loads(content)

        new_target = f"{ip}:27683"
        for item in target_list:
            if new_target in item.get('targets', []):
                return

        target_list.append({
            "targets": [new_target],
            "labels": {"region": region, "env": "prod"}
        })

        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(target_list, f, indent=4)

    def wait_for_prometheus_data(self, instance, max_retries=10, sleep_time=3):
        """轮询检查 Prometheus 是否已有该实例的 up 指标"""
        query = f'up{{instance="{instance}"}}'
        for i in range(max_retries):
            try:
                res = requests.get(PROMETHEUS_API_URL, params={'query': query})
                data = res.json()
                if data['status'] == 'success' and len(data['data']['result']) > 0:
                    # 还要确保值为 1 (健康)
                    if int(data['data']['result'][0]['value'][1]) == 1:
                        return True
            except:
                pass
            time.sleep(sleep_time)
        return False

    def query_prom(self, query):
        """通用查询包装"""
        try:
            res = requests.get(PROMETHEUS_API_URL, params={'query': query})
            res_json = res.json()
            if res_json['status'] == 'success' and res_json['data']['result']:
                return res_json['data']['result']
        except Exception as e:
            print(f"Prometheus query error: {e}")
        return []

    def collect_server_info_from_prom(self, ip, instance):
        """
        修正版：数据格式已对齐 IdcServer 模型
        """
        data = {}

        # 1. Hostname -> hostname
        # Model: hostname = models.CharField
        res = self.query_prom(f'node_uname_info{{instance="{instance}"}}')
        data['hostname'] = res[0]['metric'].get('nodename', 'unknown') if res else 'unknown'

        # 2. CPU -> cpu_count
        # Model: cpu_count = models.IntegerField
        res = self.query_prom(f'count(count(node_cpu_seconds_total{{instance="{instance}"}}) by (cpu))')
        data['cpu_count'] = int(res[0]['value'][1]) if res else 0

        # 3. Memory -> memory_count (注意字段名修改！)
        # Model: memory_count = models.FloatField
        res = self.query_prom(f'node_memory_MemTotal_bytes{{instance="{instance}"}}')
        if res:
            gb = float(res[0]['value'][1]) / 1024 / 1024 / 1024
            # Model 是 FloatField，直接传 float 即可，保留2位小数
            data['memory_count'] = round(gb, 2)
        else:
            data['memory_count'] = 0.00

        # 4. Disk -> disk_count (注意字段名修改！逻辑改为求和)
        # Model: disk_count = models.IntegerField
        # PromQL: 获取所有 ext4/xfs 文件系统的大小
        res = self.query_prom(f'node_filesystem_size_bytes{{instance="{instance}", fstype=~"ext4|xfs"}}')

        total_disk_gb = 0

        if res:
            for item in res:
                # 过滤掉 docker/kubelet 等干扰挂载点
                mountpoint = item['metric'].get('mountpoint', '')
                if '/docker/' in mountpoint or '/kubelet/' in mountpoint:
                    continue

                # 累加大小
                size_gb = float(item['value'][1]) / 1024 / 1024 / 1024
                total_disk_gb += size_gb

        # Model 是 IntegerField，所以取整
        data['disk_count'] = int(total_disk_gb)

        # 5. IP -> ip (Model 里有这个字段)
        # 既然是更新操作，且你已经有了 IP，直接使用传入的 IP 即可
        # 除非你想更新为从 Prometheus 查到的 IP（通常没必要）
        data['ip'] = ip

        return data

    def get(self, request):
        servers = IdcServer.objects.all()
        serializer = GetIdcServerSerializer(servers, many=True)
        return Response(serializer.data)

    def delete(self, request, pk):
        server = IdcServer.objects.get(id=pk)
        ip = server.ip

        if ip:
            target_to_remove = f"{ip}:27683"

            if os.path.exists(JSON_FILE_PATH):
                try:
                    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 先从每个组的 targets 列表中移除 IP
                    for group in data:
                        if 'targets' in group and target_to_remove in group['targets']:
                            group['targets'].remove(target_to_remove)

                    # 过滤掉那些 targets 为空的分组
                    # 这步操作会把 "targets": [] 的整个对象（包含 labels）都删掉
                    new_data = [group for group in data if len(group.get('targets', [])) > 0]

                    # 3. 只有数据发生了变化（长度变了，或者内容变了）才写回
                    if len(new_data) != len(data) or new_data != data:
                        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                            json.dump(new_data, f, indent=4, ensure_ascii=False)
                        print(f"Prometheus 配置已更新，移除了: {target_to_remove}")

                except Exception as e:
                    print(f"更新 Prometheus 文件出错: {e}")

        server.delete()
        return Response({'detail': '删除成功'}, status=status.HTTP_204_NO_CONTENT)


class IdcServerAPIView(APIView):

    def post(self, request):
        print('到我这里了')
        print(request.data)
        data = request.data
        hostname = data.get('hostname')
        cpu_count = data.get('cpu_count')
        mem_info = data.get('memory_count')
        disk_info = data.get('disk_count')
        ip_info = data.get('ip')
        server = IdcServer()
        server.scan_status = 2  # 默认是正常，后续再做判断
        server.hostname = hostname
        server.memory_count = mem_info
        server.disk_count = disk_info
        server.ip = ip_info
        server.function = GLOBAL_FUNCTION
        server.region = GLOBAL_REGION
        server.cpu_count = cpu_count
        server.save()
        print(hostname, cpu_count, mem_info, disk_info, ip_info, GLOBAL_FUNCTION, GLOBAL_REGION.username)

        return Response({'detail': 'success'}, status=status.HTTP_201_CREATED)


class IdcServerUpdateView(generics.RetrieveUpdateAPIView):
    queryset = IdcServer.objects.all()
    serializer_class = IdcServerUpdateSerializer


class IdcServerMonitor(APIView):
    def post(self, request):
        # 1. 获取前端传来的原始数据
        data = request.data
        raw_ip = data.get('ip')

        # 🕵️‍♂️ 强力清洗：如果取出来还是个字典，就再取一次 (兼容前端不同传参方式)
        if isinstance(raw_ip, dict):
            ip = raw_ip.get('ip')
        else:
            ip = raw_ip
        print('ip是', ip)
        # 2. 安全的时间处理
        try:
            now = int(time.time())
            # 注意：这里兼容你的前端结构 data['ip']['start_time']
            # 如果前端传的是扁平结构，需自行调整，但保留你之前的写法优先
            if isinstance(raw_ip, dict):
                start_time = int(raw_ip.get('start_time') or (now - 3600))
                end_time = int(raw_ip.get('end_time') or now)
                step_str = raw_ip.get('step', '60s')
            else:
                # 兜底逻辑
                start_time = int(data.get('start_time') or (now - 3600))
                end_time = int(data.get('end_time') or now)
                step_str = data.get('step', '60s')

        except (ValueError, TypeError, KeyError):
            return Response({"error": "Invalid timestamp format or data structure"}, status=400)

        # =======================================================
        # 🛡️ 核心代码：步长自动吸附与警告生成
        # =======================================================

        # 允许的固定档位
        allowed_grids = [1, 10, 30, 60]

        # A. 计算安全底线 (Prometheus 限制 11000 点，我们设 10000)
        duration = end_time - start_time
        min_safe_step = math.ceil(duration / 10000) if duration > 0 else 1
        print('最小步数', min_safe_step)

        # B. 解析用户请求的步长
        try:
            current_step = int(str(step_str).replace('s', ''))
        except:
            current_step = 60  # 解析失败兜底

        # C. 定义警告消息变量
        adjustment_msg = None
        step = step_str  # 默认使用用户的

        # D. 判断是否需要调整
        if current_step < min_safe_step:
            # 策略：从允许档位中找一个 "刚好 >= 安全底线" 的值
            new_step = min_safe_step  # 默认先用计算值
            found_in_grid = False

            for grid in allowed_grids:
                if grid >= min_safe_step:
                    new_step = grid
                    found_in_grid = True
                    break

            # 生成最终步长字符串
            step = f"{new_step}s"

            # ⭐⭐⭐ 生成警告消息，准备返回给前端
            # 如果连 60s 都不够用 (min_safe_step > 60)，说明查的时间太长了
            if not found_in_grid:
                adjustment_msg = f"查询范围过大({duration // 3600}h)，步长强制调整为 {new_step}s 以防止系统崩溃"
            else:
                adjustment_msg = f"步长自动优化: 申请{current_step}s -> 实发{new_step}s (数据量过大保护)"

            print('新步长', step)
            print(f"DEBUG: {adjustment_msg}")

        instance_pattern = ip

        queries = {
            "cpu_usage": f'100 - (avg by(instance) (irate(node_cpu_seconds_total{{instance=~"{instance_pattern}",mode="idle"}}[5m])) * 100)',
            "mem_usage": f'(1 - (node_memory_MemAvailable_bytes{{instance=~"{instance_pattern}"}} / node_memory_MemTotal_bytes{{instance=~"{instance_pattern}"}})) * 100',
            "fs_usage_root": f'100 - (node_filesystem_avail_bytes{{instance=~"{instance_pattern}",mountpoint="/"}} / node_filesystem_size_bytes{{instance=~"{instance_pattern}",mountpoint="/"}} * 100)',
            "load_1": f'node_load1{{instance=~"{instance_pattern}"}}',
            "load_5": f'node_load5{{instance=~"{instance_pattern}"}}',
            "load_15": f'node_load15{{instance=~"{instance_pattern}"}}',
            "disk_io_read": f'sum by(instance) (irate(node_disk_read_bytes_total{{instance=~"{instance_pattern}"}}[5m])) / 1024 / 1024',
            "disk_io_write": f'sum by(instance) (irate(node_disk_written_bytes_total{{instance=~"{instance_pattern}"}}[5m])) / 1024 / 1024',
            "net_in": f'sum by(instance) (irate(node_network_receive_bytes_total{{instance=~"{instance_pattern}",device!="lo"}}[5m])) / 1024',
            "net_out": f'sum by(instance) (irate(node_network_transmit_bytes_total{{instance=~"{instance_pattern}",device!="lo"}}[5m])) / 1024',
            "tcp_established": f'node_tcp_connection_states{{instance=~"{instance_pattern}", state="established"}}',
            "tcp_syn_recv": f'node_tcp_connection_states{{instance=~"{instance_pattern}", state="syn_recv"}}',
            "tcp_time_wait": f'node_tcp_connection_states{{instance=~"{instance_pattern}", state="time_wait"}}',
            "tcp_close_wait": f'node_tcp_connection_states{{instance=~"{instance_pattern}", state="close_wait"}}',
            "tcp_listen": f'node_tcp_connection_states{{instance=~"{instance_pattern}", state="listen"}}'
        }

        results = {}

        if adjustment_msg:
            results['sys_warning'] = adjustment_msg

        # =======================================================
        # 循环请求 Prometheus
        # =======================================================
        for key, promql in queries.items():
            try:
                response = requests.get(
                    "http://localhost:9090/api/v1/query_range",
                    params={
                        "query": promql,
                        "start": start_time,
                        "end": end_time,
                        "step": step
                    },
                    timeout=30  # 增加超时时间
                )

                if response.status_code != 200:
                    try:
                        err_msg = response.json().get('error', response.text)
                    except:
                        err_msg = response.text
                    print(f"Prometheus Error [{key}]: {err_msg}")
                    results[key] = {"times": [], "data": [], "error": err_msg}
                    continue

                data = response.json().get('data', {}).get('result', [])

                if data:
                    values = data[0].get('values', [])
                    results[key] = {
                        "times": [v[0] * 1000 for v in values],
                        "data": [round(float(v[1]), 2) if v[1] not in ["NaN", "+Inf", "-Inf"] else 0 for v in values]
                    }
                else:
                    results[key] = {"times": [], "data": []}

            except Exception as e:
                print(f"Exception querying {key}: {str(e)}")
                results[key] = {"times": [], "data": [], "error": f"Internal Error: {str(e)}"}

        return Response(results)
