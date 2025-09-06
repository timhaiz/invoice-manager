import os
import re
import io
import tempfile
import pytesseract
from PIL import Image
import pdfplumber
# from wand.image import Image as WandImage  # 暂时注释，需要正确配置ImageMagick
from datetime import datetime
import logging
from .baidu_ocr_service import BaiduOCRService
from .baidu_ocr_config import BaiduOCRConfig

logger = logging.getLogger(__name__)

class InvoiceRecognizer:
    """发票识别工具类"""
    
    @staticmethod
    def extract_text_from_image(image_path, use_baidu_ocr=True):
        """从图片中提取文本（仅使用百度OCR）
        
        Args:
            image_path: 图片文件路径
            use_baidu_ocr: 是否使用百度OCR（必须为True）
        """
        # 检查百度OCR配置
        if not BaiduOCRConfig.is_configured():
            logger.error("百度OCR API密钥未配置，无法进行文本识别")
            return ""
        
        # 仅使用百度OCR
        try:
            baidu_service = BaiduOCRService()
            success, baidu_text, raw_response = baidu_service.recognize_text(image_path)
            
            if success and baidu_text.strip():
                logger.info(f"百度OCR成功提取文本，长度: {len(baidu_text)}")
                return baidu_text.strip()
            else:
                logger.error(f"百度OCR提取失败: {baidu_text}")
                return ""
        except Exception as e:
            logger.error(f"百度OCR发生错误: {str(e)}")
            return ""
    
    @classmethod
    def extract_structured_invoice_data(cls, file_path, use_baidu_ocr=True):
        """从发票文件中提取结构化数据（仅使用百度OCR）
        
        Args:
            file_path: 文件路径（支持图片和PDF）
            use_baidu_ocr: 是否使用百度OCR
            
        Returns:
            tuple: (success, invoice_data)
        """
        # 检查百度OCR配置
        if not BaiduOCRConfig.is_configured():
            logger.error("百度OCR API密钥未配置，无法进行发票识别")
            return False, None
            
        # 检测文件类型
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 仅使用百度增值税发票识别接口
        try:
            from .baidu_ocr_service import BaiduOCRService
            baidu_service = BaiduOCRService()
            
            # 根据文件类型选择识别方法
            if file_ext == '.pdf':
                success, invoice_data, raw_response = baidu_service.recognize_vat_invoice_pdf(file_path)
            else:
                success, invoice_data, raw_response = baidu_service.recognize_vat_invoice(file_path)
            
            if success and invoice_data:
                logger.info(f"百度增值税发票识别成功: {file_path}")
                return True, invoice_data
            else:
                logger.error(f"百度增值税发票识别失败: {file_path}")
                return False, None
        except Exception as e:
            logger.error(f"百度增值税发票识别服务异常: {str(e)}")
            return False, None
    
    @staticmethod
    def preprocess_image(image):
        """图片预处理"""
        try:
            # 转换为灰度图
            if image.mode != 'L':
                image = image.convert('L')
            
            # 调整图片大小（如果太小的话）
            width, height = image.size
            if width < 800 or height < 600:
                scale_factor = max(800/width, 600/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
        except Exception as e:
            logger.error(f"图片预处理失败: {str(e)}")
            return image
    
    @staticmethod
    def extract_text_from_pdf(pdf_path, use_baidu_ocr=True):
        """从PDF中提取文本（统一使用图片OCR）
        
        Args:
            pdf_path: PDF文件路径
            use_baidu_ocr: 是否优先使用百度OCR（默认True）
        """

        
        try:
            # 直接转换为图片进行OCR
            text = InvoiceRecognizer.pdf_to_image_ocr(pdf_path, use_baidu_ocr)

            

            return text.strip()
        except Exception as e:
            logger.error(f"从PDF提取文本失败: {str(e)}")
            return ""
    
    @staticmethod
    def pdf_to_image_ocr(pdf_path, use_baidu_ocr=True):
        """将PDF转换为图片并进行OCR
        
        Args:
            pdf_path: PDF文件路径
            use_baidu_ocr: 是否优先使用百度OCR（默认True）
        """
        # 注意：此功能需要正确配置ImageMagick和Wand库
        # 当前暂时禁用，使用pdfplumber作为替代方案
        logger.warning("PDF转图片OCR功能暂时不可用，请使用pdfplumber文本提取")
        
        try:
            # 使用pdfplumber直接提取文本
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"使用pdfplumber提取PDF文本失败: {str(e)}")
            return ""
    
    @classmethod
    def extract_invoice_info(cls, text):
        """从文本中提取发票信息"""
        info = {
            'invoice_number': None,
            'invoice_content': None,  # 发票内容（原发票代码字段）
            'invoice_date': None,
            'invoice_type': None,
            'amount': None,
            'tax_amount': None,
            'total_amount': None,
            'seller_name': None,
            'seller_tax_id': None,
            'buyer_name': None,
            'buyer_tax_id': None
        }
        
        # 发票号码匹配 - 根据实际OCR结果优化
        invoice_number_patterns = [
            r'发票号码[：:：]\s*(\d{20,})',  # 20位长数字
            r'发票号码[：:：]\s*(\d{8,})',   # 8位以上数字
            r'(\d{20,})',  # 独立的20位长数字序列
            r'发票.*?号.*?[：:：]?\s*(\d{8,})',
            r'号码[：:：]\s*(\d{8,})'
        ]
        for pattern in invoice_number_patterns:
            match = re.search(pattern, text)
            if match:
                number = match.group(1)
                if len(number) >= 8:  # 发票号码至少8位
                    info['invoice_number'] = number
                    break
        
        # 发票类型识别 - 根据公司名称和内容判断
        invoice_type_patterns = {
            'ELECTRONIC': [r'电子发票', r'电子普通发票', r'滴滴', r'出行'],
            'VAT_GENERAL': [r'增值税普通发票', r'普通发票'],
            'VAT_SPECIAL': [r'增值税专用发票', r'专用发票'],
            'PAPER': [r'纸质发票']
        }
        
        for invoice_type, patterns in invoice_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    info['invoice_type'] = invoice_type
                    break
            if info['invoice_type']:
                break
        
        # 如果没有匹配到具体类型，根据其他特征判断
        if not info['invoice_type']:
            if re.search(r'电子|滴滴|出行', text):
                info['invoice_type'] = 'ELECTRONIC'
            elif re.search(r'增值税', text):
                info['invoice_type'] = 'VAT_GENERAL'
            else:
                info['invoice_type'] = 'OTHER'
        
        # 发票内容匹配 - 根据实际OCR结果优化
        content_patterns = [
            r'\*([^\*]+)\*([^\n\r]*)',  # *餐饮服务*餐饮服务格式
            r'\*([^\*]+)\*',  # 简单的*服务类型*格式
            r'项目名称[：:：]?\s*([^\n\r]+?)(?=\s*\d|$)',
            r'货物或应税劳务[、，]?服务名称[：:：]?\s*([^\n\r]+?)(?=\s*\d|$)',
            r'商品名称[：:：]?\s*([^\n\r]+?)(?=\s*\d|$)',
            r'服务名称[：:：]?\s*([^\n\r]+?)(?=\s*\d|$)',
            r'\*([^\*\n\r]+)\*[^\n\r]*?([\d,.]+)\s+([\d,.]+)\s+6%',  # 表格行中的服务项目
            r'([^\n\r]*技术服务费[^\n\r]*)',  # 直接匹配技术服务费
            r'([^\n\r]*服务费[^\n\r]*)',  # 匹配各种服务费
            r'([^\n\r]*(?:餐饮|服务|运输|客运|货运|咨询|技术|维修|安装|培训|设计)[^\n\r]*?)(?=\s*\d|$)',  # 包含服务关键词
            r'\*([^\*]+)\*\s*([\d,.]+)',  # *服务类型* 后跟数字
            r'([^\n\r]*(?:费|服务|产品|商品)[^\n\r]*?)(?=\s*[\d,.]+|$)',  # 以费、服务、产品、商品结尾的内容
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) >= 2 and '*' in pattern:
                    # 对于*服务类型*描述格式，使用第一个匹配组
                    content = match.group(1).strip()
                else:
                    content = match.group(1).strip()
                
                # 清理内容：去除多余空格和特殊字符
                content = re.sub(r'\s+', ' ', content)
                content = content.strip()
                
                if content and len(content) > 1:  # 确保内容有意义
                    info['invoice_content'] = content
                    break
        
        # 开票日期匹配 - 处理OCR识别错误
        date_patterns = [
            r'开[革票目业]?[目日业]期[：:：]?\s*(\d{4}[年洗/-]\d{1,2}[月晶/-]\d{1,2}[日晶]?)',
            r'(20\d{2}[年洗]\d{1,2}月\d{1,2}[日晶])',
            r'(\d{4}[年洗/-]\d{1,2}[月晶/-]\d{1,2}[日晶]?)'
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for date_str in matches:
                # 统一日期格式，处理OCR识别错误
                date_str = re.sub(r'[年洗]', '-', date_str)
                date_str = re.sub(r'[月晶]', '-', date_str)
                date_str = re.sub(r'[日晶]', '', date_str)
                date_str = re.sub(r'[/]', '-', date_str)
                
                try:
                    # 尝试解析日期
                    if len(date_str.split('-')) == 3:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        # 验证日期合理性（2000年后，不超过当前日期）
                        if 2000 <= date_obj.year <= datetime.now().year:
                            info['invoice_date'] = date_obj.date()
                            break
                except ValueError:
                    continue
            if 'invoice_date' in info:
                break
        
        # 销售方名称匹配 - 根据实际OCR结果优化
        seller_name_patterns = [
            r'售方[\s\n]*名称[：:：]?\s*([^\n\r]+?)(?=\s*统一社会|纳税人|$)',  # "售方 名称:" 格式
            r'销售方名称[：:：]?\s*([^\n\r]+?)(?=\s*购买方|统一社会|纳税人|$)',
            r'销售方[：:：]?\s*([^\n\r]+?)(?=\s*购买方|统一社会|纳税人|$)',
            r'开票方[：:：]?\s*([^\n\r]+?)(?=\s*收票方|$)',
            r'售方[\s\n]*名称[：:：]\s*([^\n\r]+?)(?=\s*买方|购买方|统一社会|纳税人|$)',  # 新增：处理"售方名称："格式
            r'销[\s\n]*名称[：:：]\s*([^\n\r]+?)(?=\s*买方|购买方|统一社会|纳税人|$)',  # 处理"销名称："格式
            r'([^\n\r]*(?:公司|有限|科技|文化|传播|集团|企业|商贸|贸易|出行|酒店)[^\n\r]*?)(?=\s*统一社会信用代码|纳税人识别号|$)'
        ]
        
        for pattern in seller_name_patterns:
            matches = re.findall(pattern, text)
            for seller_name in matches:
                seller_name = seller_name.strip()
                
                # 清理前缀和后缀
                seller_name = re.sub(r'^[购买销售称方名和郑：:：\s]+', '', seller_name)
                seller_name = re.sub(r'[：:：\s]*$', '', seller_name)
                
                # 提取公司名称（优先选择完整的公司名）
                company_pattern = r'([^\s]*(?:公司|有限|科技|文化|传播|集团|企业|商贸|贸易|出行)[^\s]*(?:公司|有限)?[^\s]*?)'
                company_matches = re.findall(company_pattern, seller_name)
                
                if company_matches:
                    # 选择最长的公司名称（通常更完整）
                    seller_name = max(company_matches, key=len)
                
                # 最终清理
                seller_name = re.sub(r'\s+', '', seller_name)  # 去除所有空格
                seller_name = seller_name.strip()
                
                if seller_name and len(seller_name) > 2:  # 确保名称有意义
                    info['seller_name'] = seller_name
                    break
            if info['seller_name']:
                break
        
        # 购买方名称匹配 - 根据实际OCR结果优化
        buyer_name_patterns = [
            r'买方[\s\n]*名称[：:：]?\s*([^\n\r]+?)(?=\s*统一社会|纳税人|$)',  # "买方 名称:" 格式
            r'购买方名称[：:：]?\s*([^\n\r]+?)(?=\s*销售方|纳税人识别号|统一社会信用代码|$)',
            r'购买方[：:：]?\s*([^\n\r]+?)(?=\s*销售方|纳税人识别号|统一社会信用代码|$)',
            r'收票方[：:：]?\s*([^\n\r]+?)(?=\s*开票方|$)',
            r'购[\s\n]*名称[：:：]\s*([^\n\r]+?)(?=\s*销|售方|统一社会|纳税人|$)',  # 新增：处理"购名称："格式
            r'买方[\s\n]*([^\n\r]*(?:公司|有限|科技|文化|传播|集团|企业|商贸|贸易)[^\n\r]*?)(?=\s*售方|销|统一社会|纳税人|$)',  # 处理"买方"后直接跟公司名
            r'([北京|上海|深圳|广州|天津|重庆|杭州|南京|成都|武汉][^\n\r]*(?:公司|有限|科技|文化|传播|集团|企业|商贸|贸易)[^\n\r]*?)(?=\s*统一社会信用代码|纳税人识别号|$)'
        ]
        
        for pattern in buyer_name_patterns:
            matches = re.findall(pattern, text)
            for buyer_name in matches:
                buyer_name = buyer_name.strip()
                
                # 清理前缀和后缀
                buyer_name = re.sub(r'^[购买销售称方名自得和：:：\s]+', '', buyer_name)
                buyer_name = re.sub(r'[：:：\s]*$', '', buyer_name)
                buyer_name = re.sub(r'\s*(销售|开票|和\s*名).*$', '', buyer_name)  # 去除后面的销售方信息
                
                # 提取公司名称
                company_pattern = r'([^\s]*(?:公司|有限|科技|文化|传播|集团|企业|商贸|贸易)[^\s]*(?:公司|有限)?[^\s]*?)'
                company_matches = re.findall(company_pattern, buyer_name)
                
                if company_matches:
                    # 选择最长的公司名称
                    buyer_name = max(company_matches, key=len)
                
                # 最终清理
                buyer_name = re.sub(r'\s+', '', buyer_name)  # 去除所有空格
                buyer_name = buyer_name.strip()
                
                if buyer_name and len(buyer_name) > 2:  # 确保名称有意义
                    info['buyer_name'] = buyer_name
                    break
            if info['buyer_name']:
                break
        
        # 税额匹配 - 根据实际OCR结果优化
        tax_patterns = [
            r'\*[^\*]+\*[^\n]*?([\d,.]+)\s+([\d,.]+)\s+6%\s+([\d,.]+)',  # 表格行格式：金额 金额 6% 税额
            r'合\s*计\s*￥?([\d,.]+)\s*￥?([\d,.]+)',  # 合计行格式：￥390.38 ￥23.42
            r'税额[：:]\s*￥?([\d,.]+)',
            r'([\d,.]+)\s+6%\s+([\d,.]+)'  # 简化的金额 6% 税额格式
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text)
            if match:
                if '6%' in pattern and len(match.groups()) >= 2:  # 包含税率的格式，取最后一个（税额）
                    tax_str = match.group(-1).replace(',', '')
                elif '合' in pattern and len(match.groups()) >= 2:  # 合计行格式，取第二个（税额）
                    tax_str = match.group(2).replace(',', '')
                else:
                    tax_str = match.group(1).replace(',', '')
                try:
                    info['tax_amount'] = float(tax_str)
                    break
                except ValueError:
                    continue
        
        # 价税合计匹配 - 根据实际OCR结果优化
        total_patterns = [
            r'\(\s*小[写可]?\s*\)?\s*[¥￥]?([\d,.]+)',  # (小写)￥413.80 格式
            r'价税[会合]计[（(]?[大小][写可][）)]?.*?[¥￥]?([\d,.]+)',
            r'(价税[会合]计|合计)[：:]\s*[¥￥]?([\d,.]+)',
            r'☒[^\n]*?([\d,.]+)圆[\d]*角\s*整'  # ☒肆佰壹拾叁圆捌角整格式，提取数字
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) >= 2:
                    total_str = match.group(2).replace(',', '')
                else:
                    total_str = match.group(1).replace(',', '')
                try:
                    info['total_amount'] = float(total_str)
                    break
                except ValueError:
                    continue
        
        # 如果没有匹配到价税合计，尝试从(小写)行提取
        if not info['total_amount']:
            small_amount_match = re.search(r'\(小写\)[¥￥]?([\d,.]+)', text)
            if small_amount_match:
                try:
                    info['total_amount'] = float(small_amount_match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # 金额匹配 - 提取不含税金额
        if not info['amount']:
            amount_patterns = [
                r'\*[^\*]+\*[^\n]*?([\d,.]+)\s+([\d,.]+)\s+6%',  # 表格行格式中的第一个金额
                r'合\s*计\s*￥?([\d,.]+)\s*￥?[\d,.]+',  # 合计行的第一个金额
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        info['amount'] = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue
        
        # 销售方税号匹配
        if not info['seller_tax_id']:
            seller_tax_patterns = [
                r'售方[\s\n]*.*?统一社会信用代码/纳税人识别号[：:：]?\s*([A-Z0-9]{15,18})',
                r'销售方.*?统一社会信用代码[：:：]?\s*([A-Z0-9]{15,18})',
                r'统一社会信用代码/纳税人识别号[：:：]?\s*([A-Z0-9]{15,18})'  # 第一个出现的税号通常是销售方
            ]
            for pattern in seller_tax_patterns:
                match = re.search(pattern, text)
                if match:
                    info['seller_tax_id'] = match.group(1)
                    break
        
        # 购买方税号匹配
        if not info['buyer_tax_id']:
            # 查找所有税号，第二个通常是购买方的
            all_tax_ids = re.findall(r'统一社会信用代码/纳税人识别号[：:：]?\s*([A-Z0-9]{15,18})', text)
            if len(all_tax_ids) >= 2:
                info['buyer_tax_id'] = all_tax_ids[1]  # 第二个税号是购买方
            elif len(all_tax_ids) == 1 and not info['seller_tax_id']:
                # 如果只有一个税号且销售方税号未设置，则这个是购买方的
                info['buyer_tax_id'] = all_tax_ids[0]
        
        # 清理None值，避免在JSON序列化时变成字符串'None'
        for key, value in info.items():
            if value is None:
                info[key] = ''
        
        return info
    
    @classmethod
    def recognize_invoice(cls, file_path, use_baidu_ocr=True):
        """识别发票文件
        
        Args:
            file_path: 文件路径
            use_baidu_ocr: 是否使用百度OCR
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.pdf']:
            # PDF文件：直接使用结构化识别（支持PDF）
            success, invoice_info = cls.extract_structured_invoice_data(file_path, use_baidu_ocr)
            
            if success:
                # 获取原始文本用于记录
                text = cls.extract_text_from_pdf(file_path, use_baidu_ocr)
                return invoice_info, text
            else:
                return None, "无法识别发票内容"
                
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            # 优先使用结构化发票识别
            success, invoice_info = cls.extract_structured_invoice_data(file_path, use_baidu_ocr)
            if success:
                # 如果结构化识别成功，同时获取原始文本用于记录
                text = cls.extract_text_from_image(file_path, use_baidu_ocr)
                return invoice_info, text
            else:
                return None, "无法识别发票内容"
        else:
            logger.error(f"不支持的文件类型: {file_ext}")
            return None, "不支持的文件类型"


class InvoiceValidator:
    """发票验证工具类"""
    
    @staticmethod
    def validate_invoice_number(invoice_number):
        """验证发票号码格式"""
        if not invoice_number:
            return False
        return bool(re.match(r'^\d{8}$', invoice_number))
    
    @staticmethod
    def validate_tax_id(tax_id):
        """验证税号格式"""
        if not tax_id:
            return False
        # 统一社会信用代码（18位）或者纳税人识别号（15位）
        return bool(re.match(r'^[A-Z0-9]{15,18}$', tax_id))
    
    @staticmethod
    def check_duplicate(invoice_number):
        """检查是否有重复发票（主要检查发票号码）"""
        from .models import Invoice
        if invoice_number:
            return Invoice.objects.filter(invoice_number=invoice_number).exists()
        return False
    
    @staticmethod
    def validate_company_info(buyer_name, buyer_tax_id, company):
        """验证公司信息是否匹配"""
        if not company:
            return True  # 如果没有指定公司，则不验证
        
        # 检查公司名称
        name_match = buyer_name and company.name in buyer_name
        
        # 检查税号
        tax_match = buyer_tax_id and company.tax_id == buyer_tax_id
        
        return name_match and tax_match