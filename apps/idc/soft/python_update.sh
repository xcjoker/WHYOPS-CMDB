#!/bin/bash

# 定义安装OpenSSL的函数
install_openssl() {
    echo "安装依赖包..."
    yum install -y openssl-devel bzip2-devel expat-devel gdbm-devel readline-devel sqlite-devel
    echo "下载并安装OpenSSL..."
    wget https://www.openssl.org/source/old/1.1.1/openssl-1.1.1.tar.gz
    tar -xzvf openssl-1.1.1.tar.gz -C /usr/local/src
    cd /usr/local/src/openssl-1.1.1
    ./config shared zlib --prefix=/usr/local/openssl && make && make install
    echo "export PATH=\$PATH:/usr/local/openssl/bin" >> /etc/profile
    echo "export LD_LIBRARY_PATH=/usr/local/openssl/lib:\$LD_LIBRARY_PATH" >> /etc/profile
    ldconfig
    source /etc/profile
}

# 检查OpenSSL是否已经安装
which openssl
if [ $? -ne 0 ]; then
  install_openssl
fi

# 获取OpenSSL版本号并去除非数字部分
openssl_version=$(openssl version | awk '{print $2}' | sed -r 's/([0-9.]+).*/\1/')

# 检查OpenSSL版本是否正确
if [ "$(printf "1.1.1\n$openssl_version\n" | sort -V | head -n1)" != "1.1.1" ]; then
    yum remove openssl -y  2&1 > /dev/null
    echo "OpenSSL版本过低，正在安装OpenSSL..."
    install_openssl
fi

# 检查Python是否已经安装
which python3
if [ $? -eq 0 ]; then
  python_version=$(python3 -V 2>&1 | awk '{print $2}' | sed -r 's/([0-9.]+).*/\1/')
  if [ "$(printf "3.7.3\n$python_version\n" | sort -V | head -n1)" != "3.7.3" ]; then
      echo "Python版本不是3.7.3，需要重新安装Python..."
      cd /usr/local/src/Python-3.7.3
                  make clean
      ./configure --prefix=/usr/local/python3 --with-openssl=/usr/local/openssl  && make && make install
      pip3.7 install requests psutil distro
  else
      echo "Python版本正确。"
  fi
else
  echo "Python未安装，需要重新安装Python..."
  cd /root
  if [ ! -f './Python-3.7.3.tgz' ]; then
      echo "本地没有Python源码包，需要远程下载，请耐心等待...\n"
      wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
  fi
  tar -xzvf Python-3.7.3.tgz -C /usr/local/src/
  cd /usr/local/src/Python-3.7.3
  ./configure --prefix=/usr/local/python3 --with-openssl=/usr/local/openssl && make && make install
  echo "export PATH=/usr/local/python3/bin:\$PATH" >> /etc/profile
  source /etc/profile
  pip3.7 install requests psutil distro
fi
