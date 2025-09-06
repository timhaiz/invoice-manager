# encoding:utf-8
"""
百度OCR服务类
"""

import requests
import base64
import json
import time
import logging
import re
from datetime import datetime
from django.core.cache import cache
from .baidu_ocr_config import BaiduOCRConfig

logger = logging.getLogger(__name__)

class BaiduOCRService:
    """百度OCR服务类"""
    
    def __init__(self):
        self.config = BaiduOCRConfig
        self._access_token = None
        self._token_expires_at = 0
    
    def get_access_token(self):
        """获取访问令牌"""
        # 先从缓存中获取token
        cached_token = cache.get('baidu_ocr_access_token')
        if cached_token:
            return cached_token
        
        # 如果缓存中没有，则请求新的token
        if not self.config.is_configured():
            logger.error("百度OCR API密钥未配置")
            return None
        
        try:
            response = requests.post(
                 self.config.TOKEN_URL,
                 data=self.config.get_token_params(),
                 timeout=self.config.TIMEOUT
             )
            
            if response.status_code == 200:
                result = response.json()
                if 'access_token' in result:
                    access_token = result['access_token']
                    expires_in = result.get('expires_in', 2592000)  # 默认30天
                    
                    # 将token存入缓存，提前5分钟过期以避免边界情况
                    cache.set('baidu_ocr_access_token', access_token, expires_in - 300)
                    
                    logger.info("百度OCR访问令牌获取成功")
                    return access_token
                else:
                    logger.error(f"获取访问令牌失败: {result}")
                    return None
            else:
                logger.error(f"请求访问令牌失败，状态码: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"请求访问令牌时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取访问令牌时发生未知错误: {str(e)}")
            return None
    
    def image_to_base64(self, image_path):
        """将图片文件转换为base64编码"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
                return base64.b64encode(image_data)
        except Exception as e:
            logger.error(f"图片转换base64失败: {str(e)}")
            return None
    
    def pdf_to_base64(self, pdf_path, urlencoded=False):
        """将PDF文件转换为base64编码
        
        Args:
            pdf_path: PDF文件路径
            urlencoded: 是否对结果进行URL编码
            
        Returns:
            str: base64编码的字符串
        """
        try:
            with open(pdf_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf8")
                if urlencoded:
                    import urllib.parse
                    content = urllib.parse.quote_plus(content)
                return content
        except Exception as e:
            logger.error(f"PDF转换base64失败: {str(e)}")
            return None
    
    def recognize_text(self, image_path, use_accurate=False):
        """识别图片中的文字
        
        Args:
            image_path: 图片文件路径
            use_accurate: 是否使用高精度OCR（收费更高但准确率更高）
            
        Returns:
            tuple: (success, result_text, raw_response)
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, "无法获取访问令牌", None
        
        # 将图片转换为base64
        image_base64 = self.image_to_base64(image_path)
        if not image_base64:
            return False, "图片转换失败", None
        
        # 选择OCR接口
        ocr_url = self.config.ACCURATE_OCR_URL if use_accurate else self.config.GENERAL_OCR_URL
        request_url = f"{ocr_url}?access_token={access_token}"
        
        # 准备请求参数
        params = {"image": image_base64}
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(
                request_url,
                data=params,
                headers=headers,
                timeout=self.config.TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查是否有错误
                if 'error_code' in result:
                    error_msg = result.get('error_msg', '未知错误')
                    logger.error(f"百度OCR识别失败: {error_msg}")
                    return False, f"OCR识别失败: {error_msg}", result
                
                # 提取文字内容
                if 'words_result' in result:
                    text_lines = []
                    for item in result['words_result']:
                        if 'words' in item:
                            text_lines.append(item['words'])
                    
                    full_text = '\n'.join(text_lines)
                    logger.info(f"百度OCR识别成功，提取到 {len(text_lines)} 行文字")
                    return True, full_text, result
                else:
                    logger.warning("OCR响应中没有找到文字结果")
                    return False, "未识别到文字内容", result
            else:
                logger.error(f"OCR请求失败，状态码: {response.status_code}")
                return False, f"请求失败，状态码: {response.status_code}", None
                
        except requests.RequestException as e:
            logger.error(f"OCR请求时发生网络错误: {str(e)}")
            return False, f"网络错误: {str(e)}", None
        except Exception as e:
            logger.error(f"OCR识别时发生未知错误: {str(e)}")
            return False, f"未知错误: {str(e)}", None
    
    def recognize_vat_invoice(self, image_path):
        """识别增值税发票
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            tuple: (success, structured_data, raw_response)
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, None, None
        
        # 将图片转换为base64
        image_base64 = self.image_to_base64(image_path)
        if not image_base64:
            return False, None, None
        
        # 使用增值税发票识别接口
        request_url = f"{self.config.VAT_INVOICE_URL}?access_token={access_token}"
        
        # 准备请求参数
        params = {"image": image_base64}
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(
                request_url,
                data=params,
                headers=headers,
                timeout=self.config.TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查是否有错误
                if 'error_code' in result:
                    error_msg = result.get('error_msg', '未知错误')
                    logger.error(f"百度增值税发票识别失败: {error_msg}")
                    return False, None, result
                
                # 提取结构化发票信息
                if 'words_result' in result:

                    
                    invoice_data = self._parse_vat_invoice_result(result['words_result'])
                    logger.info("百度增值税发票识别成功")
                    return True, invoice_data, result
                else:
                    logger.warning("增值税发票识别响应中没有找到结果")
                    return False, None, result
            else:
                logger.error(f"增值税发票识别请求失败，状态码: {response.status_code}")
                return False, None, None
                
        except requests.RequestException as e:
            logger.error(f"增值税发票识别请求时发生网络错误: {str(e)}")
            return False, None, None
        except Exception as e:
            logger.error(f"增值税发票识别时发生未知错误: {str(e)}")
            return False, None, None
    
    def recognize_vat_invoice_pdf(self, pdf_path, seal_tag=False):
        """识别PDF格式的增值税发票
        
        Args:
            pdf_path: PDF文件路径
            seal_tag: 是否检测印章（默认False）
            
        Returns:
            tuple: (success, structured_data, raw_response)
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, None, None
        
        # 将PDF转换为base64（URL编码）
        pdf_base64 = self.pdf_to_base64(pdf_path, urlencoded=True)
        if not pdf_base64:
            return False, None, None
        
        # 使用增值税发票识别接口
        request_url = f"{self.config.VAT_INVOICE_URL}?access_token={access_token}"
        
        # 准备请求参数（按照百度官方示例格式）
        payload = f'pdf_file={pdf_base64}&seal_tag={str(seal_tag).lower()}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(
                request_url,
                headers=headers,
                data=payload,
                timeout=self.config.TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查是否有错误
                if 'error_code' in result:
                    error_msg = result.get('error_msg', '未知错误')
                    logger.error(f"百度PDF增值税发票识别失败: {error_msg}")
                    return False, None, result
                
                # 提取结构化发票信息
                if 'words_result' in result:

                    
                    invoice_data = self._parse_vat_invoice_result(result['words_result'])
                    logger.info("百度PDF增值税发票识别成功")
                    return True, invoice_data, result
                else:
                    logger.warning("PDF增值税发票识别响应中没有找到结果")
                    return False, None, result
            else:
                logger.error(f"PDF增值税发票识别请求失败，状态码: {response.status_code}")
                return False, None, None
                
        except requests.RequestException as e:
            logger.error(f"PDF增值税发票识别请求时发生网络错误: {str(e)}")
            return False, None, None
        except Exception as e:
            logger.error(f"PDF增值税发票识别时发生未知错误: {str(e)}")
            return False, None, None
    
    def _parse_vat_invoice_result(self, words_result):
        """解析增值税发票识别结果
        
        Args:
            words_result: 百度OCR返回的words_result字段
            
        Returns:
            dict: 结构化的发票信息
        """
        invoice_data = {
            'invoice_number': '',
            'invoice_content': '',
            'invoice_date': '',
            'invoice_type': 'VAT_GENERAL',
            'amount': '',
            'tax_amount': '',
            'total_amount': '',
            'seller_name': '',
            'seller_tax_id': '',
            'buyer_name': '',
            'buyer_tax_id': ''
        }
        
        # 直接从words_result中提取字段值的辅助函数
        def get_field_value(field_name):
            if field_name in words_result:
                field_data = words_result[field_name]
                if isinstance(field_data, dict) and 'words' in field_data:
                    return field_data['words'].strip()
                elif isinstance(field_data, str):
                    return field_data.strip()
            return ''
        
        # 百度增值税发票识别API返回的字段映射
        # 基于官方文档：https://ai.baidu.com/tech/ocr_receipts/vat_invoice
        invoice_data['invoice_number'] = get_field_value('InvoiceNum')  # 发票号码
        
        # 开票日期处理 - 转换中文格式为YYYY-MM-DD格式
        raw_date = get_field_value('InvoiceDate')
        invoice_data['invoice_date'] = self._convert_date_format(raw_date)
        
        # 发票类型映射
        invoice_type_raw = get_field_value('InvoiceType')
        if '专用' in invoice_type_raw:
            invoice_data['invoice_type'] = 'VAT_SPECIAL'
        elif '普通' in invoice_type_raw:
            invoice_data['invoice_type'] = 'VAT_GENERAL'
        else:
            invoice_data['invoice_type'] = 'VAT_GENERAL'  # 默认普通发票
        
        # 金额字段处理 - 根据百度API文档修正
        # TotalAmount: 合计金额(不含税)
        # TotalTax: 合计税额
        # AmountInFiguers: 价税合计(小写数字)
        # AmountInWords: 价税合计(大写汉字)
        invoice_data['amount'] = get_field_value('TotalAmount')        # 不含税金额
        invoice_data['tax_amount'] = get_field_value('TotalTax')       # 税额
        invoice_data['total_amount'] = get_field_value('AmountInFiguers')  # 价税合计
        
        # 销售方信息
        invoice_data['seller_name'] = get_field_value('SellerName')           # 销售方名称
        invoice_data['seller_tax_id'] = get_field_value('SellerRegisterNum')  # 销售方纳税人识别号
        
        # 购买方信息
        invoice_data['buyer_name'] = get_field_value('PurchaserName')           # 购买方名称
        invoice_data['buyer_tax_id'] = get_field_value('PurchaserRegisterNum')  # 购买方纳税人识别号
        
        # 处理商品信息作为发票内容
        commodity_names = []
        if 'CommodityName' in words_result:
            commodity_data = words_result['CommodityName']
            if isinstance(commodity_data, list):
                for item in commodity_data:
                    if isinstance(item, dict) and 'word' in item:
                        commodity_names.append(item['word'])
                    elif isinstance(item, dict) and 'words' in item:
                        commodity_names.append(item['words'])
            elif isinstance(commodity_data, dict):
                if 'word' in commodity_data:
                    commodity_names.append(commodity_data['word'])
                elif 'words' in commodity_data:
                    commodity_names.append(commodity_data['words'])
        
        if commodity_names:
            invoice_data['invoice_content'] = ', '.join(commodity_names)
        
        # 确保所有字段都不为None或空字符串
        for key, value in invoice_data.items():
            if value is None or value == 'None':
                invoice_data[key] = ''
        
        return invoice_data
    
    def _convert_date_format(self, date_str):
        """将中文日期格式转换为YYYY-MM-DD格式
        
        Args:
            date_str: 中文格式的日期字符串，如"2025年03月20日"
            
        Returns:
            str: YYYY-MM-DD格式的日期字符串，如"2025-03-20"
        """
        if not date_str:
            return ''
        
        try:
            # 处理中文日期格式：2025年03月20日
            chinese_date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日?'
            match = re.search(chinese_date_pattern, date_str)
            
            if match:
                year, month, day = match.groups()
                # 确保月份和日期是两位数
                month = month.zfill(2)
                day = day.zfill(2)
                formatted_date = f"{year}-{month}-{day}"
                
                # 验证日期有效性
                datetime.strptime(formatted_date, '%Y-%m-%d')
                return formatted_date
            
            # 处理其他可能的格式：YYYY-MM-DD, YYYY/MM/DD等
            other_patterns = [
                r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
                r'(\d{4})(\d{2})(\d{2})'
            ]
            
            for pattern in other_patterns:
                match = re.search(pattern, date_str)
                if match:
                    year, month, day = match.groups()
                    month = month.zfill(2)
                    day = day.zfill(2)
                    formatted_date = f"{year}-{month}-{day}"
                    
                    # 验证日期有效性
                    datetime.strptime(formatted_date, '%Y-%m-%d')
                    return formatted_date
            
            # 如果无法解析，返回原始字符串
            logger.warning(f"无法解析日期格式: {date_str}")
            return date_str
            
        except Exception as e:
            logger.error(f"日期格式转换失败: {date_str}, 错误: {str(e)}")
            return date_str
    
    def batch_recognize(self, image_paths, use_accurate=False):
        """批量识别多个图片
        
        Args:
            image_paths: 图片文件路径列表
            use_accurate: 是否使用高精度OCR
            
        Returns:
            list: 每个图片的识别结果列表
        """
        results = []
        for image_path in image_paths:
            success, text, raw_response = self.recognize_text(image_path, use_accurate)
            results.append({
                'image_path': image_path,
                'success': success,
                'text': text,
                'raw_response': raw_response
            })
            
            # 添加小延迟避免请求过于频繁
            time.sleep(0.1)
        
        return results