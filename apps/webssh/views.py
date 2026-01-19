from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import paramiko


# Create your views here.
class WebSSHView(APIView):
    def post(self, request):
        # 获取请求数据
        data = request.data
        print(data)
        ip = data.get('ip')
        password = data.get('password')
        user = data.get('user')

        # 创建 SSH 客户端
        ssh_client = paramiko.SSHClient()

        # # 载入系统的 SSH 密钥
        # ssh_client.load_system_host_keys()

        # 允许连接不在 known_hosts 中的主机（如果你信任目标主机）
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # 尝试连接到目标服务器
            ssh_client.connect(ip, 22, user, password, timeout=6)
            # 连接成功
            ssh_client.close()
            return Response({'detail': 'SSH连接成功'}, status=status.HTTP_200_OK)
        except paramiko.AuthenticationException:
            return Response({'detail': '身份验证失败，请检查您的用户名和密码'}, status=status.HTTP_401_UNAUTHORIZED)
        except paramiko.SSHException as e:

            return Response({'detail': f'SSH连接失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'detail': f'发生错误, 请联系管理员: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

