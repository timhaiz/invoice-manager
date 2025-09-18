@echo off
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
call venv\Scripts\activate.bat

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
echo venv\Scripts\activate.bat ^&^& python manage.py createsuperuser
echo 然后运行以下命令启动服务:
echo venv\Scripts\activate.bat ^&^& python manage.py runserver 0.0.0.0:8000
pause
