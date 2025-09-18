# 生产环境配置文件模板
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
