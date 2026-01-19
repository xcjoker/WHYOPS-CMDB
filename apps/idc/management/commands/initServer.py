from django.core.management.base import BaseCommand
from apps.idc.models import IdcServer, IdcRegion

class Command(BaseCommand):
    def handle(self, *args, **options):
        region = IdcRegion.objects.get(id=1)

        server = IdcServer()
        server.hostname = 'k8s-master'
        server.ip = '192.168.239.123'
        server.function = 'k8s的master节点'
        server.memory_count = 32
        server.cpu_count = 16
        server.region = region
        server.scan_status = 0
        server.disk_count = 128
        server.save()
        self.stdout.write('server添加成功')
