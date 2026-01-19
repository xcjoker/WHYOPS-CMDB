import json
import threading
import socket
from channels.generic.websocket import WebsocketConsumer
import paramiko


class TerminalConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssh_client = None
        self.channel = None
        self.should_keep_reading = False

    def connect(self):
        # 建立 WebSocket 连接
        self.accept()

    def disconnect(self, close_code):
        self.should_keep_reading = False
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass

    def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                return

            if 'ip' in data:
                self.ssh_connect(data)
            elif 'command' in data:
                command = data['command']
                if self.channel and self.channel.active:
                    self.channel.send(command)

    def ssh_connect(self, data):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(
                data['ip'],
                22,
                data['username'],
                data['password'],
                timeout=10
            )

            self.channel = self.ssh_client.invoke_shell(
                term='xterm',
                width=80,
                height=24
            )
            self.channel.settimeout(0.1)

            self.should_keep_reading = True
            # 开启独立线程读取 SSH 数据
            threading.Thread(target=self.loop_read, daemon=True).start()

            self.send(json.dumps({'message': 'Connect Success\r\n'}))

        except Exception as e:
            error_msg = f"SSH connection failed: {str(e)}\r\n"
            self.send(json.dumps({'message': error_msg}))
            self.close()

    def loop_read(self):
        while self.should_keep_reading:
            if self.channel and self.channel.active:
                try:
                    recv_data = self.channel.recv(10240)
                    if len(recv_data) > 0:
                        message = recv_data.decode('utf-8', errors='ignore')
                        self.send(text_data=message)
                    else:
                        pass
                except socket.timeout:
                    pass
                except Exception as e:
                    break
            else:
                break