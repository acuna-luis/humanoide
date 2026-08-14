#!/bin/bash

#给images.sh添加可执行权限 chmod +x images.sh

#运行images.sh命令 ./images.sh

set -ex
echo "开始解压images.tar.gz文件..."
tar -xzf utars-udoke-config-v0.2.0_offline.tar.gz

echo "解压完成,进入images目录..."
cd images

echo "在192.168.11.2服务器上新建images目录"
ssh walker@192.168.11.2 << EOF
  mkdir -p /home/walker/images
EOF



echo "开始复制motion.tar到远程服务器..."
scp motion.tar walker@192.168.11.2:/home/walker/images/

echo "复制完成，开始在本地导入vision.tar镜像..."
docker load -i vision.tar

echo "本地镜像导入完成，开始在远程服务器导入motion.tar镜像..."
ssh walker@192.168.11.2 << EOF
  cd /home/walker/images
  echo "在远程服务器导入motion.tar镜像..."
  docker load -i motion.tar
  echo "远程镜像导入完成"
EOF

echo "所有操作已完成！"
exit 0