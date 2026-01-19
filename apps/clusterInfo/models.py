from django.db import models

# Create your models here.

class Cluster(models.Model):
    IMPORT_STATUS_CHOICES = (
        ('success', '导入成功'),
        ('failed', '导入失败'),
        ('pending', '导入中'),
    )

    CLUSTER_STATUS_CHOICES = (
        ('running', '就绪'),
        ('abnormal', '异常'),
        ('unknown', '下线'),
    )

    name = models.CharField(max_length=100, verbose_name="集群名称", unique=True)
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    version = models.CharField(max_length=50, verbose_name="集群版本", help_text="例如 v1.25.7+k3s1")
    kubeconfig = models.TextField(verbose_name="KubeConfig配置")
    api_server = models.CharField(max_length=255, verbose_name="API Server地址", blank=True, null=True)

    import_status = models.CharField(
        max_length=20,
        choices=IMPORT_STATUS_CHOICES,
        default='success',
        verbose_name="导入状态"
    )

    cluster_status = models.CharField(
        max_length=20,
        choices=CLUSTER_STATUS_CHOICES,
        default='running',
        verbose_name="集群状态"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "K8s集群"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Node(models.Model):
    ROLE_CHOICES = (
        ('master', 'Master'),
        ('worker', 'Worker'),
    )
    STATUS_CHOICES = (
        ('Ready', 'Ready'),
        ('NotReady', 'NotReady'),
        ('Unknown', 'Unknown'),
    )

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='nodes', verbose_name="所属集群")
    name = models.CharField(max_length=255, verbose_name="节点名称(主机名)")
    ip_address = models.GenericIPAddressField(verbose_name="IP地址")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker', verbose_name="节点角色")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Unknown', verbose_name="节点状态")
    cpu_cores = models.IntegerField(verbose_name="CPU逻辑核心数", default=0)
    disk_total = models.CharField(max_length=50, verbose_name="磁盘容量", default="0Gi")
    memory = models.CharField(max_length=50, verbose_name="内存配置")

    # 额外存储一些信息，方便后续扩展
    os_image = models.CharField(max_length=255, null=True, blank=True, verbose_name="操作系统")
    kernel_version = models.CharField(max_length=100, null=True, blank=True, verbose_name="内核版本")

    class Meta:
        verbose_name = "集群节点"
        verbose_name_plural = verbose_name
        unique_together = ('cluster', 'name')  # 同一个集群下节点名唯一

    def __str__(self):
        return f"{self.cluster.name} - {self.name}"
