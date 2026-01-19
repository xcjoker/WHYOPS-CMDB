from django.core.management.base import BaseCommand
from apps.oaauth.models import OAUser, OADepartment


class Command(BaseCommand):
    def handle(self, *args, **options):
        boarder = OADepartment.objects.get(name='董事会', intro="董事会")
        developer = OADepartment.objects.get(name='产品开发部', intro="产品设计，技术开发")
        operator = OADepartment.objects.get(name='运营部', intro="客户运营，产品运营")
        saler = OADepartment.objects.get(name='销售部', intro="销售产品")
        hr = OADepartment.objects.get(name='人事部', intro="员工招聘，员工培训，员工考核")
        finance = OADepartment.objects.get(name='财务部', intro="财务报表，财务审核")

        dongdong = OAUser.objects.create_superuser(email="dongdong@qq.com", realname='东东', password="111111",
                                                   department=boarder)

        duoduo = OAUser.objects.create_superuser(email="duoduo@qq.com", realname="多多", password="111111",
                                                 department=boarder)

        zhangsan = OAUser.objects.create_user(email="zhangsan@qq.com", realname="张三", password="111111",
                                              department=developer)

        lisi = OAUser.objects.create_user(email="lisi@qq.com", realname="李四", password="111111", department=operator)

        wangwu = OAUser.objects.create_user(email="wangwu@qq.com", realname="王五", password="111111",
                                            department=hr)

        zhaoliu = OAUser.objects.create_user(email="zhaoliu@qq.com", realname="赵六", password="111111",
                                             department=finance)

        sunqi = OAUser.objects.create_user(email="sunqi@qq.com", realname="孙七", password="111111",
                                           department=saler)

        boarder.leader = dongdong
        boarder.manager = None

        developer.leader = zhangsan
        developer.manager = dongdong

        operator.leader = lisi
        operator.manager = dongdong

        saler.leader = sunqi
        saler.manager = dongdong

        hr.leader = wangwu
        hr.manager = duoduo

        finance.leader = zhaoliu
        finance.manager = duoduo

        boarder.save()
        developer.save()
        operator.save()
        saler.save()
        hr.save()
        finance.save()

        self.stdout.write('初始用户创建成功')