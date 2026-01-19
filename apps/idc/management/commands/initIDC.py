from django.core.management.base import BaseCommand
from apps.idc.models import IdcRegion


class Command(BaseCommand):
    def handle(self, *args, **options):
        IdcRegion.objects.create(
            address='香港',
            username='香泽',
            username_phone='18975218160',
            server_count=2
        )
        self.stdout.write('添加数据成功')
