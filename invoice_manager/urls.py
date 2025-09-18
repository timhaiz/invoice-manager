"""invoice_manager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# 添加受保护的媒体文件访问路由（必须在其他路径之前）
from invoice.views import protected_media_view

urlpatterns = [
    # 受保护的媒体文件访问路由（优先级最高）
    path('media/<path:file_path>', protected_media_view, name='protected_media'),
    
    # 其他路由
    path('admin/', admin.site.urls),
    path('', include('invoice.urls')),
]

# 添加静态文件的URL配置（仅在DEBUG模式下）
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)