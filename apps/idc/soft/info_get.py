import psutil
import platform
import os
import json
import requests

class GetData(object):
    def __init__(self):
        self.ret = {}
    def get_hostname(self):
        return platform.node()

    def get_cpu_count(self):
        return psutil.cpu_count(logical=False)

    def get_mem_info(self):
        return '%.2f' %(psutil.virtual_memory().total/1024/1024/1024)

    def get_disk_info(self):
        disk_name_list = []
        disk_size_list = []
        disk_name_file = os.popen("lsblk | grep disk | awk '{print $1}' | sed 's/G//'")
        disk_size_file = os.popen("lsblk | grep disk | awk '{print $4}' | sed 's/G//'")
        for disk_name in disk_name_file.readlines():
            disk_name_list.append(disk_name.split()[0])
            for disk_size in disk_size_file.readlines():
                disk_size_list.append(disk_size.split()[0])
        return dict(zip(disk_name_list, disk_size_list))

    def get_ip_info(self):
        ret = {}
        for net_name in psutil.net_if_addrs():
            ret[net_name] = psutil.net_if_addrs()[net_name][0].address
        return ret

    def send_data(self):
        data_dict = GetData.__dict__
        for key, value in data_dict.items():
            if 'get_' in key:
                key = key.replace('get_','')
                self.ret[key] = value(self)
        return self.ret

def send_data(url, data):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)  # Django REST framework 期望的是
    # application/json 类型的请求，而默认情况下，requests.post 不会自动将 Content-Type 设置为 application/json，所以你仍然需要手动指定 Content-Type 为
    # application/json
    print(response.text)

if __name__ == '__main__':
    getdata = GetData().send_data()
    print(getdata)
    send_data(url='http://192.168.239.1:8000/idc/server/api/', data=json.dumps(getdata))
