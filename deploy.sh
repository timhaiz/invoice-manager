#!/bin/bash
# 发票管理系统部署脚本

set -e

echo "开始部署发票管理系统..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.9+"
    exit 1
fi

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 数据库迁移
echo "执行数据库迁移..."
python manage.py migrate

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput

echo "部署完成！"
echo "请运行以下命令创建管理员用户:"
echo "source venv/bin/activate && python manage.py createsuperuser"
echo "然后运行以下命令启动服务:"
echo "source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
