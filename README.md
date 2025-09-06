# 发票识别管理系统

基于Django和百度OCR API的发票自动识别和管理工具。

## 功能特性

- 📄 支持多种发票格式识别（增值税发票、普通发票等）
- 🔍 基于百度OCR API的高精度文字识别
- 📊 发票信息自动提取和结构化存储
- 🗂️ 发票文件管理和分类
- 📱 响应式Web界面
- 🔐 用户认证和权限管理

## 技术栈

- **后端**: Django 3.2+
- **数据库**: SQLite (可扩展至PostgreSQL/MySQL)
- **前端**: Bootstrap 4 + jQuery
- **OCR服务**: 百度智能云OCR API
- **文件处理**: PDF解析和图像处理

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd invoice-manager

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并配置以下环境变量：

```env
# 百度OCR API配置
BAIDU_OCR_APP_ID=your_app_id
BAIDU_OCR_API_KEY=your_api_key
BAIDU_OCR_SECRET_KEY=your_secret_key

# Django配置
DJANGO_SECRET_KEY=your_secret_key
DEBUG=True
```

### 3. 数据库初始化

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 4. 运行项目

```bash
python manage.py runserver
```

访问 http://127.0.0.1:8000 查看应用。

## 百度OCR API配置

1. 注册百度智能云账号：https://cloud.baidu.com/
2. 创建OCR应用获取API密钥
3. 在环境变量中配置API密钥信息

## 项目结构

```
invoice-manager/
├── invoice/                 # 主应用
│   ├── models.py           # 数据模型
│   ├── views.py            # 视图逻辑
│   ├── forms.py            # 表单定义
│   ├── baidu_ocr_service.py # OCR服务
│   └── templates/          # 模板文件
├── invoice_manager/        # 项目配置
├── static/                 # 静态文件
├── media/                  # 媒体文件
├── requirements.txt        # 依赖包
└── manage.py              # Django管理脚本
```

## 部署说明

### 生产环境配置

1. 设置 `DEBUG=False`
2. 配置允许的主机 `ALLOWED_HOSTS`
3. 使用PostgreSQL或MySQL数据库
4. 配置静态文件服务
5. 使用HTTPS协议

### 环境变量

生产环境必须配置的环境变量：

- `BAIDU_OCR_APP_ID`: 百度OCR应用ID
- `BAIDU_OCR_API_KEY`: 百度OCR API密钥
- `BAIDU_OCR_SECRET_KEY`: 百度OCR密钥
- `DJANGO_SECRET_KEY`: Django密钥
- `DEBUG`: 调试模式（生产环境设为False）

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 创建 Pull Request

## 更新日志

### v1.0.0
- 初始版本发布
- 基础发票识别功能
- Web管理界面
- 百度OCR集成