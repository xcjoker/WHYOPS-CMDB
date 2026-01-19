from django.db import models
import requests

class IdcRegion(models.Model):
    address = models.CharField(max_length=64, verbose_name="机房地址")
    username = models.CharField(max_length=32, verbose_name="机房负责人姓名")
    username_phone = models.CharField(max_length=11, verbose_name="机房负责人手机号")
    server_count = models.IntegerField(default=0, verbose_name="服务器数量")

    # --- 新增字段 ---
    longitude = models.FloatField(verbose_name="经度", null=True, blank=True)
    latitude = models.FloatField(verbose_name="纬度", null=True, blank=True)

    def save(self, *args, **kwargs):
        # 逻辑：只有当地址存在，且(是新记录 或 坐标为空 或 地址变更了)时，才去请求API
        # 为了简单，这里判断：只要有地址且没坐标，就去查。
        # 如果你想更智能（比如修改地址后自动更新），可以对比数据库里的旧值，这里先做基础版

        if self.address and (not self.longitude or not self.latitude):
            try:
                # ⚠️ 请替换为你申请的高德 Web服务 Key
                amap_key = '85c83912b81f45bdf3a1189b20d0370b'
                city = ''  # 如果需要限定城市，可以填
                url = f'https://restapi.amap.com/v3/geocode/geo?address={self.address}&key={amap_key}'

                response = requests.get(url, timeout=5)
                res_json = response.json()

                if res_json.get('status') == '1' and res_json.get('geocodes'):
                    # 高德返回格式 "经度,纬度"
                    location = res_json['geocodes'][0]['location'].split(',')
                    self.longitude = float(location[0])
                    self.latitude = float(location[1])
            except Exception as e:
                print(f"高德API调用失败: {str(e)}")
                # 失败了不阻断保存，只是没有坐标

        super().save(*args, **kwargs)

class IdcServer(models.Model):
    hostname = models.CharField(max_length=20, verbose_name="主机名称")
    ip = models.GenericIPAddressField(verbose_name="ip地址", protocol="IPv4")
    cpu_count = models.IntegerField(verbose_name="CPU个数")
    memory_count = models.FloatField(verbose_name="内存大小")
    disk_count = models.IntegerField(verbose_name="磁盘大小")
    region = models.ForeignKey(IdcRegion, verbose_name="", on_delete=models.CASCADE)
    function = models.TextField(verbose_name="服务器作用")
    scan_status_list = [
        (0, '异常'),
        (1, '故障'),
        (2, '正常')
    ]
    scan_status = models.IntegerField(choices=scan_status_list, default=2, verbose_name="扫描状态")