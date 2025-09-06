#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票管理系统部署打包脚本
自动创建部署包，排除不必要的文件和目录
"""

import os
import shutil
import zipfile
import datetime
from pathlib import Path

# 需要排除的文件和目录
EXCLUDE_PATTERNS = {
    # Mac系统文件
    '.DS_Store',
    '._*',
    '.Spotlight-V100',
    '.Trashes',
    '.fseventsd',
    '.TemporaryItems',
    '.VolumeIcon.icns',
    
    # Python相关
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.Python',
    'pip-log.txt',
    'pip-delete-this-directory.txt',
    
    # 虚拟环境
    '.venv',
    'venv',
    'env',
    '.env',
    
    # IDE和编辑器
    '.vscode',
    '.idea',
    '*.swp',
    '*.swo',
    '*~',
    '.project',
    '.pydevproject',
    
    # 版本控制
    '.git',
    '.gitignore',
    '.svn',
    '.hg',
    
    # 日志和临时文件
    '*.log',
    '*.tmp',
    '*.temp',
    'django_errors.log',
    
    # 数据库文件（开发用）
    'db.sqlite3',
    '*.db',
    
    # 媒体文件（可选，根据需要调整）
    # 'media',
    
    # 测试文件
    'test_*.py',
    '*_test.py',
    'tests.py',
    
    # 其他
    '.coverage',
    'htmlcov',
    '.pytest_cache',
    '.tox',
    'node_modules',
    '*.egg-info',
    'dist',
    'build',
    
    # 部署相关（避免重复打包）
    'deploy_packages',
    'create_deployment_package.py'
}

# 需要包含的重要文件（即使匹配排除模式也要包含）
INCLUDE_FORCE = {
    'requirements.txt',
    'manage.py',
    'README.md'
}

def should_exclude(path, base_path):
    """
    判断文件或目录是否应该被排除
    """
    rel_path = os.path.relpath(path, base_path)
    name = os.path.basename(path)
    
    # 强制包含的文件
    if name in INCLUDE_FORCE:
        return False
    
    # 检查排除模式
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*.'):
            # 文件扩展名模式
            if name.endswith(pattern[1:]):
                return True
        elif pattern.startswith('._'):
            # Mac隐藏文件模式
            if name.startswith('._'):
                return True
        elif pattern.startswith('*'):
            # 通配符模式
            if pattern[1:] in name:
                return True
        else:
            # 精确匹配
            if name == pattern or rel_path.startswith(pattern):
                return True
    
    return False

def copy_project(src_dir, dest_dir):
    """
    复制项目文件，排除不必要的文件
    """
    copied_files = []
    excluded_files = []
    
    for root, dirs, files in os.walk(src_dir):
        # 过滤目录
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d), src_dir)]
        
        for file in files:
            src_file = os.path.join(root, file)
            
            if should_exclude(src_file, src_dir):
                excluded_files.append(os.path.relpath(src_file, src_dir))
                continue
            
            # 计算目标路径
            rel_path = os.path.relpath(src_file, src_dir)
            dest_file = os.path.join(dest_dir, rel_path)
            
            # 创建目标目录
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            
            # 复制文件
            shutil.copy2(src_file, dest_file)
            copied_files.append(rel_path)
    
    return copied_files, excluded_files

def create_deployment_info(dest_dir, copied_files, excluded_files):
    """
    创建部署信息文件
    """
    info_content = f"""# 发票管理系统部署包信息

## 打包时间
{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 包含的文件数量
总计: {len(copied_files)} 个文件

## 排除的文件类型
- Mac系统文件 (.DS_Store, ._* 等)
- Python缓存文件 (__pycache__, *.pyc 等)
- 虚拟环境目录 (.venv, venv 等)
- IDE配置文件 (.vscode, .idea 等)
- 版本控制文件 (.git, .svn 等)
- 日志和临时文件 (*.log, *.tmp 等)
- 开发数据库文件 (db.sqlite3)
- 测试文件 (test_*.py, *_test.py)

## 部署前准备
1. 安装Python 3.9+
2. 创建虚拟环境: python -m venv venv
3. 激活虚拟环境: source venv/bin/activate (Linux/Mac) 或 venv\\Scripts\\activate (Windows)
4. 安装依赖: pip install -r requirements.txt
5. 配置数据库: python manage.py migrate
6. 创建超级用户: python manage.py createsuperuser
7. 收集静态文件: python manage.py collectstatic
8. 启动服务: python manage.py runserver 0.0.0.0:8000

## 生产环境配置建议
1. 修改 settings.py 中的 DEBUG = False
2. 设置 ALLOWED_HOSTS
3. 配置生产数据库（PostgreSQL/MySQL）
4. 配置静态文件服务（Nginx）
5. 使用 WSGI 服务器（Gunicorn/uWSGI）
6. 配置 HTTPS
7. 设置环境变量保护敏感信息

## 排除的文件列表
{chr(10).join(f'- {f}' for f in excluded_files[:50])}{'...' if len(excluded_files) > 50 else ''}
"""
    
    with open(os.path.join(dest_dir, 'DEPLOYMENT_INFO.md'), 'w', encoding='utf-8') as f:
        f.write(info_content)

def create_production_settings(dest_dir):
    """
    创建生产环境配置文件模板
    """
    settings_content = '''# 生产环境配置文件模板
# 复制此文件为 production_settings.py 并根据实际环境修改

from .settings import *

# 生产环境设置
DEBUG = False

# 允许的主机（必须设置）
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com',
    'your-server-ip',
]

# 数据库配置（生产环境建议使用PostgreSQL或MySQL）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'invoice_db',
        'USER': 'invoice_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 静态文件配置
STATIC_ROOT = '/var/www/invoice/static/'
MEDIA_ROOT = '/var/www/invoice/media/'

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS设置（如果使用HTTPS）
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/invoice/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
'''
    
    settings_dir = os.path.join(dest_dir, 'invoice_manager')
    with open(os.path.join(settings_dir, 'production_settings_template.py'), 'w', encoding='utf-8') as f:
        f.write(settings_content)

def create_deployment_scripts(dest_dir):
    """
    创建部署脚本
    """
    # Linux部署脚本
    deploy_script = '''#!/bin/bash
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
'''
    
    with open(os.path.join(dest_dir, 'deploy.sh'), 'w', encoding='utf-8') as f:
        f.write(deploy_script)
    
    # 设置执行权限
    os.chmod(os.path.join(dest_dir, 'deploy.sh'), 0o755)
    
    # Windows部署脚本
    deploy_bat = '''@echo off
echo 开始部署发票管理系统...

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 创建虚拟环境
echo 创建虚拟环境...
python -m venv venv
call venv\\Scripts\\activate.bat

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip

REM 安装依赖
echo 安装Python依赖...
pip install -r requirements.txt

REM 数据库迁移
echo 执行数据库迁移...
python manage.py migrate

REM 收集静态文件
echo 收集静态文件...
python manage.py collectstatic --noinput

echo 部署完成！
echo 请运行以下命令创建管理员用户:
echo venv\\Scripts\\activate.bat ^&^& python manage.py createsuperuser
echo 然后运行以下命令启动服务:
echo venv\\Scripts\\activate.bat ^&^& python manage.py runserver 0.0.0.0:8000
pause
'''
    
    with open(os.path.join(dest_dir, 'deploy.bat'), 'w', encoding='utf-8') as f:
        f.write(deploy_bat)

def main():
    """
    主函数
    """
    # 获取当前项目目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建部署包目录
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    package_name = f'invoice_system_deployment_{timestamp}'
    package_dir = os.path.join(project_dir, 'deploy_packages', package_name)
    
    print(f"创建部署包: {package_name}")
    print(f"源目录: {project_dir}")
    print(f"目标目录: {package_dir}")
    
    # 创建目标目录
    os.makedirs(package_dir, exist_ok=True)
    
    # 复制项目文件
    print("\n正在复制项目文件...")
    copied_files, excluded_files = copy_project(project_dir, package_dir)
    
    print(f"✓ 复制了 {len(copied_files)} 个文件")
    print(f"✓ 排除了 {len(excluded_files)} 个文件")
    
    # 创建部署信息文件
    print("\n创建部署信息文件...")
    create_deployment_info(package_dir, copied_files, excluded_files)
    
    # 创建生产环境配置模板
    print("创建生产环境配置模板...")
    create_production_settings(package_dir)
    
    # 创建部署脚本
    print("创建部署脚本...")
    create_deployment_scripts(package_dir)
    
    # 创建ZIP压缩包
    print("\n创建ZIP压缩包...")
    zip_path = f"{package_dir}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, os.path.dirname(package_dir))
                zipf.write(file_path, arc_path)
    
    # 计算文件大小
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
    
    print(f"\n✅ 部署包创建完成！")
    print(f"📁 目录: {package_dir}")
    print(f"📦 压缩包: {zip_path}")
    print(f"📊 大小: {zip_size:.2f} MB")
    print(f"\n🚀 部署说明:")
    print(f"1. 将 {package_name}.zip 上传到服务器")
    print(f"2. 解压: unzip {package_name}.zip")
    print(f"3. 进入目录: cd {package_name}")
    print(f"4. 运行部署脚本: ./deploy.sh (Linux) 或 deploy.bat (Windows)")
    print(f"5. 查看 DEPLOYMENT_INFO.md 了解详细部署说明")

if __name__ == '__main__':
    main()