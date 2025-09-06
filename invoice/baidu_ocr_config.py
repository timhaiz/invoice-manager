# encoding:utf-8
"""
百度OCR API配置文件
"""

import os
from django.conf import settings

# 百度OCR API配置
class BaiduOCRConfig:
    # API端点配置
    TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
    GENERAL_OCR_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'
    ACCURATE_OCR_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic'
    # 增值税发票识别专用接口
    VAT_INVOICE_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice'
    
    # 请求配置
    TIMEOUT = 30  # 请求超时时间（秒）
    MAX_RETRIES = 3  # 最大重试次数
    
    @classmethod
    def get_app_id(cls):
        """获取APP_ID"""
        try:
            return getattr(settings, 'BAIDU_OCR_APP_ID', os.getenv('BAIDU_OCR_APP_ID', ''))
        except:
            return os.getenv('BAIDU_OCR_APP_ID', '')
    
    @classmethod
    def get_api_key(cls):
        """获取API_KEY"""
        try:
            return getattr(settings, 'BAIDU_OCR_API_KEY', os.getenv('BAIDU_OCR_API_KEY', ''))
        except:
            return os.getenv('BAIDU_OCR_API_KEY', '')
    
    @classmethod
    def get_secret_key(cls):
        """获取SECRET_KEY"""
        try:
            return getattr(settings, 'BAIDU_OCR_SECRET_KEY', os.getenv('BAIDU_OCR_SECRET_KEY', ''))
        except:
            return os.getenv('BAIDU_OCR_SECRET_KEY', '')
    
    @classmethod
    def is_configured(cls):
        """检查是否已正确配置API密钥"""
        return bool(cls.get_api_key() and cls.get_secret_key())
    
    @classmethod
    def get_token_params(cls):
        """获取token请求参数"""
        return {
            'grant_type': 'client_credentials',
            'client_id': cls.get_api_key(),
            'client_secret': cls.get_secret_key()
        }