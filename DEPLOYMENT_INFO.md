# 发票管理系统部署包信息

## 打包时间
2025-09-18 13:13:11

## 包含的文件数量
总计: 242 个文件

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
3. 激活虚拟环境: source venv/bin/activate (Linux/Mac) 或 venv\Scripts\activate (Windows)
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
- .env.example
- django_errors.log
- create_deployment_package.py
- db.sqlite3
- .env
- .gitignore
- invoice/tests.py
