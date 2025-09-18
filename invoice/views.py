from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.conf import settings

from .models import Company, InvoiceCategory, Invoice, InvoiceRecognition
from .utils import InvoiceRecognizer, InvoiceValidator
from .forms import InvoiceForm

import os
import json
from datetime import datetime, timedelta
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

# 首页视图
@login_required
def index(request):
    # 统计数据
    invoice_count = Invoice.objects.count()
    total_amount = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    category_stats = InvoiceCategory.objects.annotate(invoice_count=Count('invoice'))
    recent_invoices = Invoice.objects.order_by('-created_at')[:5]
    
    context = {
        'invoice_count': invoice_count,
        'total_amount': total_amount,

        'category_stats': category_stats,
        'recent_invoices': recent_invoices,
    }
    return render(request, 'invoice/index.html', context)

# 发票列表视图
@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('category').prefetch_related('recognitions').all().order_by('-invoice_date')
    
    # 筛选条件
    category_id = request.GET.get('category')
    if category_id:
        invoices = invoices.filter(category_id=category_id)
    
    buyer_company = request.GET.get('buyer_company')
    if buyer_company:
        invoices = invoices.filter(buyer_name=buyer_company)
    
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    # 关键词搜索
    search = request.GET.get('search')
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(invoice_content__icontains=search) |
            Q(seller_name__icontains=search) |
            Q(buyer_name__icontains=search)
        )
    
    # 按销售方搜索
    seller = request.GET.get('seller')
    if seller:
        invoices = invoices.filter(seller_name__icontains=seller)
    
    # 按购买方搜索
    buyer = request.GET.get('buyer')
    if buyer:
        invoices = invoices.filter(buyer_name__icontains=buyer)
    
    start_date = request.GET.get('start_date')
    if start_date:
        try:
            # 解析年月格式 (YYYY-MM)
            start_date_obj = datetime.strptime(start_date, '%Y-%m')
            # 获取该月的第一天
            start_date = start_date_obj.date()
            invoices = invoices.filter(invoice_date__gte=start_date)
        except ValueError:
            pass
    
    end_date = request.GET.get('end_date')
    if end_date:
        try:
            # 解析年月格式 (YYYY-MM)
            end_date_obj = datetime.strptime(end_date, '%Y-%m')
            # 获取该月的最后一天
            if end_date_obj.month == 12:
                next_month = end_date_obj.replace(year=end_date_obj.year + 1, month=1)
            else:
                next_month = end_date_obj.replace(month=end_date_obj.month + 1)
            end_date = (next_month - timedelta(days=1)).date()
            invoices = invoices.filter(invoice_date__lte=end_date)
        except ValueError:
            pass
    
    # 分页
    page_size = request.GET.get('page_size', '20')  # 默认每页显示20条
    try:
        page_size = int(page_size)
        # 限制分页大小在合理范围内
        if page_size not in [20, 40, 80, 500]:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20
    
    paginator = Paginator(invoices, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取所有类别和购买方公司，用于筛选
    categories = InvoiceCategory.objects.all()
    # 获取所有购买方公司（从发票中的buyer_name去重）
    buyer_companies = Invoice.objects.values('buyer_name').distinct().exclude(buyer_name__isnull=True).exclude(buyer_name='').order_by('buyer_name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'buyer_companies': buyer_companies,
        'invoice_status_choices': Invoice.STATUS_CHOICES,
        'current_page_size': page_size,
        'page_size_choices': [20, 40, 80, 500],
    }
    return render(request, 'invoice/invoice_list.html', context)

# 发票详情视图
@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('recognitions'), pk=pk)
    context = {'invoice': invoice}
    return render(request, 'invoice/invoice_detail.html', context)

# 添加发票视图
@login_required
def invoice_add(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                invoice = form.save(commit=False)
                invoice.created_by = request.user
                invoice.save()
                messages.success(request, '发票添加成功')
                return redirect('invoice:invoice_detail', pk=invoice.pk)
            except Exception as e:
                logger.error(f"添加发票失败: {str(e)}")
                messages.error(request, f'添加发票失败: {str(e)}')
        else:
            # 表单验证失败，显示错误信息
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        form = InvoiceForm()
    
    context = {
        'form': form,
    }
    return render(request, 'invoice/invoice_form.html', context)

# 编辑发票视图
@login_required
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        # 处理表单提交
        invoice.invoice_number = request.POST.get('invoice_number')
        invoice.invoice_content = request.POST.get('invoice_content')
        invoice.invoice_date = datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date()
        invoice.invoice_type = request.POST.get('invoice_type')
        invoice.amount = float(request.POST.get('amount'))
        invoice.tax_amount = float(request.POST.get('tax_amount') or 0)
        invoice.total_amount = float(request.POST.get('total_amount') or invoice.amount + invoice.tax_amount)
        invoice.seller_name = request.POST.get('seller_name')
        invoice.seller_tax_id = request.POST.get('seller_tax_id')
        invoice.buyer_name = request.POST.get('buyer_name')
        invoice.buyer_tax_id = request.POST.get('buyer_tax_id')
        invoice.description = request.POST.get('description')
        
        category_id = request.POST.get('category')
        if category_id:
            invoice.category_id = category_id
        else:
            invoice.category = None
        
        company_id = request.POST.get('company')
        if company_id:
            invoice.company_id = company_id
        else:
            invoice.company = None
        
        # 处理上传的文件
        if 'file' in request.FILES:
            invoice.file = request.FILES['file']
        if 'image' in request.FILES:
            invoice.image = request.FILES['image']
        
        invoice.save()
        messages.success(request, '发票更新成功')
        return redirect('invoice:invoice_detail', pk=invoice.pk)
    
    # GET请求，显示表单
    categories = InvoiceCategory.objects.all()
    # 获取所有购买方公司（从发票中的buyer_name去重）
    buyer_companies = Invoice.objects.values('buyer_name').distinct().exclude(buyer_name__isnull=True).exclude(buyer_name='').order_by('buyer_name')
    context = {
        'invoice': invoice,
        'categories': categories,
        'buyer_companies': buyer_companies,
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
    }
    return render(request, 'invoice/invoice_edit.html', context)

# 删除发票视图
@login_required
@require_POST
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.delete()
    messages.success(request, '发票已删除')
    return redirect('invoice:invoice_list')


# 受保护的媒体文件服务视图
def protected_media_view(request, file_path):
    """
    受保护的媒体文件访问视图
    只有登录用户才能访问媒体文件，未登录用户返回404
    """
    import mimetypes
    from django.http import Http404, FileResponse
    
    # 检查用户是否登录，未登录直接返回404
    if not request.user.is_authenticated:
        logger.warning(f"未登录用户尝试访问媒体文件: {file_path}")
        raise Http404("页面不存在")
    
    # 构建完整的文件路径
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    # 检查文件是否存在
    if not os.path.exists(full_path):
        logger.warning(f"用户 {request.user.username} 尝试访问不存在的文件: {file_path}")
        raise Http404("文件不存在")
    
    # 检查文件是否在MEDIA_ROOT目录内（防止路径遍历攻击）
    if not os.path.abspath(full_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        logger.warning(f"用户 {request.user.username} 尝试访问非法路径: {file_path}")
        raise Http404("非法访问")
    
    # 记录访问日志
    logger.info(f"用户 {request.user.username} 访问媒体文件: {file_path}")
    
    # 获取文件的MIME类型
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # 返回文件响应
    try:
        response = FileResponse(
            open(full_path, 'rb'),
            content_type=content_type,
            as_attachment=False  # 设置为False允许在浏览器中查看，True则强制下载
        )
        
        # 设置文件名
        filename = os.path.basename(file_path)
        if request.GET.get('download') == '1':
            # 如果URL参数包含download=1，则强制下载
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            # 否则允许在浏览器中查看
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"访问媒体文件失败: {str(e)}")
        raise Http404("文件访问失败")


def auto_confirm_recognition(recognition, user):
    """
    自动确认识别结果，创建发票记录
    """
    try:
        invoice_info = json.loads(recognition.result)
    except json.JSONDecodeError:
        logger.error(f"识别结果格式错误，无法自动确认: {recognition.pk}")
        return None
    
    # 检查必要字段
    required_fields = ['invoice_number', 'amount', 'invoice_date']
    for field in required_fields:
        if not invoice_info.get(field):
            logger.warning(f"缺少必要字段 {field}，无法自动确认: {recognition.pk}")
            return None
    
    # 检查是否有重复发票（综合多个字段判断）
    original_invoice_number = invoice_info.get('invoice_number')
    seller_name = invoice_info.get('seller_name')
    amount = invoice_info.get('total_amount') or invoice_info.get('amount')
    invoice_date_str = invoice_info.get('invoice_date')
    
    # 解析日期用于重复检查
    invoice_date_for_check = None
    if invoice_date_str:
        try:
            if isinstance(invoice_date_str, str):
                date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']
                for fmt in date_formats:
                    try:
                        invoice_date_for_check = datetime.strptime(invoice_date_str, fmt).date()
                        break
                    except ValueError:
                        continue
            else:
                invoice_date_for_check = invoice_date_str
        except Exception:
            pass
    
    # 检查重复发票
    if InvoiceValidator.check_duplicate(original_invoice_number, seller_name, amount, invoice_date_for_check):
        logger.warning(f"发票重复，拒绝自动确认: {original_invoice_number} (销售方: {seller_name}, 金额: {amount})")
        return None
    
    try:
        # 使用之前解析的日期或重新解析
        invoice_date = invoice_date_for_check
        if not invoice_date and invoice_date_str:
            logger.warning(f"无法解析日期格式，无法自动确认: {invoice_date_str}")
            return None
        
        # 创建发票对象
        invoice = Invoice(
            invoice_number=invoice_info.get('invoice_number'),
            invoice_content=invoice_info.get('invoice_content', ''),
            invoice_date=invoice_date,
            invoice_type=invoice_info.get('invoice_type', 'ELECTRONIC'),
            amount=float(invoice_info.get('amount', 0)),
            tax_amount=float(invoice_info.get('tax_amount', 0)),
            total_amount=float(invoice_info.get('total_amount', 0)),
            seller_name=invoice_info.get('seller_name', ''),
            seller_tax_id=invoice_info.get('seller_tax_id', ''),
            buyer_name=invoice_info.get('buyer_name', ''),
            buyer_tax_id=invoice_info.get('buyer_tax_id', ''),
            description=invoice_info.get('description', ''),
            created_by=user
        )
        
        # 使用识别记录中的文件
        invoice.file = recognition.file
        
        invoice.save()
        
        # 更新识别记录关联的发票
        recognition.invoice = invoice
        recognition.save()
        
        logger.info(f"自动确认发票成功: {invoice.invoice_number}")
        return invoice
        
    except Exception as e:
        logger.error(f"自动确认发票失败: {str(e)}")
        return None

# 下载发票文件视图
@login_required
def download_invoice_file(request, pk):
    """下载发票识别记录的原始文件"""
    # 添加详细的调试日志
    logger.info(f"下载请求开始 - 用户: {request.user}, 是否认证: {request.user.is_authenticated}, PK: {pk}")
    logger.info(f"请求方法: {request.method}, 请求路径: {request.path}")
    logger.info(f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    
    try:
        recognition = get_object_or_404(InvoiceRecognition, pk=pk)
        logger.info(f"找到识别记录: {recognition}")
        
        if not recognition.file:
            messages.error(request, '该记录没有关联的文件')
            return redirect('invoice:invoice_list')
        
        # 检查文件是否存在
        if not os.path.exists(recognition.file.path):
            messages.error(request, '文件不存在或已被删除')
            return redirect('invoice:invoice_list')
        
        # 获取文件信息
        file_path = recognition.file.path
        file_name = os.path.basename(file_path)
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # 设置响应头
        response = HttpResponse(file_content)
        
        # 根据文件扩展名设置正确的MIME类型
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext == '.pdf':
            response['Content-Type'] = 'application/pdf'
        elif file_ext in ['.jpg', '.jpeg']:
            response['Content-Type'] = 'image/jpeg'
        elif file_ext == '.png':
            response['Content-Type'] = 'image/png'
        else:
            response['Content-Type'] = 'application/octet-stream'
        
        # 使用更通用的文件名处理方式，同时提供ASCII和UTF-8文件名
        # 创建一个安全的ASCII文件名作为fallback
        safe_filename = ''.join(c if c.isascii() and (c.isalnum() or c in '.-_') else '_' for c in file_name)
        if not safe_filename or safe_filename == '_' * len(safe_filename):
            # 如果文件名全是特殊字符，使用默认名称
            file_ext = os.path.splitext(file_name)[1] if '.' in file_name else ''
            safe_filename = f'invoice_file{file_ext}'
        
        # 使用双重文件名格式：ASCII fallback + UTF-8编码
        encoded_filename = quote(file_name.encode('utf-8'))
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        response['Content-Length'] = len(file_content)
        
        # 添加调试日志
        logger.info(f"用户 {request.user.username} 下载了发票文件: {file_name}")
        logger.info(f"Content-Disposition: attachment; filename*=UTF-8''{encoded_filename}")
        logger.info(f"Content-Type: {response['Content-Type']}")
        return response
        
    except Exception as e:
        logger.error(f"下载发票文件失败: {str(e)}")
        messages.error(request, f'下载文件失败: {str(e)}')
        return redirect('invoice:invoice_list')

# 批量下载发票文件视图
@login_required
@csrf_protect
def batch_download_invoice_files(request):
    """批量下载发票文件"""
    # 支持GET和POST方法，支持recognition_ids和invoice_ids参数
    if request.method == 'POST':
        recognition_ids = request.POST.getlist('recognition_ids')
        invoice_ids = request.POST.getlist('invoice_ids')
    else:
        recognition_ids = request.GET.getlist('recognition_ids')
        invoice_ids = request.GET.getlist('invoice_ids')
    
    # 如果传入的是发票ID，需要转换为识别记录ID
    if invoice_ids and not recognition_ids:
        try:
            # 通过发票ID获取对应的识别记录ID
            invoices = Invoice.objects.filter(id__in=invoice_ids).prefetch_related('recognitions')
            recognition_ids = []
            for invoice in invoices:
                # 获取每个发票的识别记录
                for recognition in invoice.recognitions.all():
                    recognition_ids.append(str(recognition.id))
        except Exception as e:
            logger.error(f"获取识别记录失败: {str(e)}")
            messages.error(request, '获取发票文件失败')
            return redirect('invoice:invoice_list')
    
    if not recognition_ids:
        messages.error(request, '请选择要下载的文件')
        return redirect('invoice:invoice_list')
    
    try:
        import zipfile
        from io import BytesIO
        
        # 创建ZIP文件
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            file_count = 0
            for recognition_id in recognition_ids:
                try:
                    recognition = InvoiceRecognition.objects.get(pk=recognition_id)
                    
                    if recognition.file and os.path.exists(recognition.file.path):
                        file_path = recognition.file.path
                        file_name = os.path.basename(file_path)
                        
                        # 如果文件名重复，添加序号
                        base_name, ext = os.path.splitext(file_name)
                        counter = 1
                        original_file_name = file_name
                        while file_name in [info.filename for info in zip_file.infolist()]:
                            file_name = f"{base_name}_{counter}{ext}"
                            counter += 1
                        
                        # 添加文件到ZIP
                        zip_file.write(file_path, file_name)
                        file_count += 1
                        
                except InvoiceRecognition.DoesNotExist:
                    continue
                except Exception as e:
                    logger.warning(f"添加文件到ZIP失败: {str(e)}")
                    continue
        
        if file_count == 0:
            messages.error(request, '没有找到可下载的文件')
            return redirect('invoice:invoice_list')
        
        zip_buffer.seek(0)
        
        # 设置响应头
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        zip_filename = f'发票文件_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        
        # 使用更通用的文件名处理方式，提供ASCII fallback
        safe_filename = f'invoice_files_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        encoded_filename = quote(zip_filename.encode('utf-8'))
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        
        # 添加调试日志
        logger.info(f"批量下载ZIP文件名: {zip_filename}")
        logger.info(f"Content-Disposition: attachment; filename*=UTF-8''{encoded_filename}")
        
        logger.info(f"用户 {request.user.username} 批量下载了 {file_count} 个发票文件")
        return response
        
    except Exception as e:
        logger.error(f"批量下载发票文件失败: {str(e)}")
        messages.error(request, f'批量下载失败: {str(e)}')
        return redirect('invoice:invoice_list')


@login_required
def manual_input(request, recognition_ids):
    """手动填写发票信息视图"""
    # 解析识别记录ID
    try:
        recognition_id_list = [int(id.strip()) for id in recognition_ids.split(',') if id.strip()]
    except ValueError:
        messages.error(request, '无效的识别记录ID')
        return redirect('invoice:invoice_recognize')
    
    # 获取识别记录
    recognitions = InvoiceRecognition.objects.filter(
        pk__in=recognition_id_list,
        created_by=request.user
    ).order_by('created_at')
    
    if not recognitions.exists():
        messages.error(request, '未找到相关的识别记录')
        return redirect('invoice:invoice_recognize')
    
    if request.method == 'POST':
        # 处理表单提交
        saved_count = 0
        errors = []
        
        for recognition in recognitions:
            try:
                # 获取表单数据
                prefix = f'recognition_{recognition.pk}'
                
                # 检查是否选中了这个识别记录
                if not request.POST.get(f'{prefix}_selected'):
                    continue
                
                # 创建发票对象
                invoice = Invoice(
                    invoice_number=request.POST.get(f'{prefix}_invoice_number', '').strip(),
                    invoice_date=request.POST.get(f'{prefix}_invoice_date') or None,
                    total_amount=request.POST.get(f'{prefix}_total_amount') or 0,
                    tax_amount=request.POST.get(f'{prefix}_tax_amount') or 0,
                    amount=request.POST.get(f'{prefix}_amount_without_tax') or 0,
                    seller_name=request.POST.get(f'{prefix}_seller_name', '').strip(),
                    seller_tax_id=request.POST.get(f'{prefix}_seller_tax_number', '').strip(),
                    buyer_name=request.POST.get(f'{prefix}_buyer_name', '').strip(),
                    buyer_tax_id=request.POST.get(f'{prefix}_buyer_tax_number', '').strip(),
                    description=request.POST.get(f'{prefix}_description', '').strip(),
                    invoice_type='OTHER',  # 默认类型
                    created_by=request.user
                )
                
                # 设置分类
                category_id = request.POST.get(f'{prefix}_category')
                if category_id:
                    try:
                        invoice.category = InvoiceCategory.objects.get(pk=category_id)
                    except InvoiceCategory.DoesNotExist:
                        pass
                
                # 验证必填字段
                if not invoice.invoice_number:
                    errors.append(f'文件 {recognition.file.name}: 发票号码不能为空')
                    continue
                
                if not invoice.seller_name:
                    errors.append(f'文件 {recognition.file.name}: 销售方名称不能为空')
                    continue
                
                if not invoice.buyer_name:
                    errors.append(f'文件 {recognition.file.name}: 购买方名称不能为空')
                    continue
                
                # 保存发票
                invoice.save()
                
                # 更新识别记录状态
                recognition.status = 'MANUAL_COMPLETED'
                recognition.save()
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"手动保存发票失败 {recognition.file.name}: {str(e)}")
                errors.append(f'文件 {recognition.file.name}: {str(e)}')
        
        # 显示结果消息
        if saved_count > 0:
            messages.success(request, f'成功保存 {saved_count} 张发票')
        
        if errors:
            messages.error(request, '\n'.join(errors))
        
        # 如果全部处理完成，返回发票列表
        if saved_count > 0 and not errors:
            return redirect('invoice:invoice_list')
    
    # 获取发票分类
    categories = InvoiceCategory.objects.all()
    
    # 准备识别记录数据
    recognition_data = []
    for recognition in recognitions:
        data = {
            'recognition': recognition,
            'filename': os.path.basename(recognition.file.name) if recognition.file else '未知文件',
            'status_display': recognition.get_status_display(),
            'error_message': recognition.result if recognition.status == 'FAILED' else None,
        }
        
        # 如果有识别结果，尝试解析
        if recognition.status == 'COMPLETED' and recognition.result:
            try:
                parsed_result = json.loads(recognition.result)
                data['parsed_result'] = parsed_result
            except (json.JSONDecodeError, TypeError):
                data['parsed_result'] = None
        else:
            data['parsed_result'] = None
        
        recognition_data.append(data)
    
    context = {
        'recognition_data': recognition_data,
        'categories': categories,
        'recognition_ids': recognition_ids,
    }
    
    return render(request, 'invoice/manual_input.html', context)

# 发票识别上传视图
@login_required
def invoice_recognize(request):
    if request.method == 'POST':
        # 检查百度OCR配置
        from .baidu_ocr_config import BaiduOCRConfig
        if not BaiduOCRConfig.is_configured():
            messages.error(request, '百度OCR API密钥未配置，请联系管理员配置后再使用发票识别功能')
            return redirect('invoice:invoice_recognize')
            
        # 检查是否有文件上传
        if 'files' not in request.FILES:
            messages.error(request, '请选择要上传的文件')
            return redirect('invoice:invoice_recognize')
        
        uploaded_files = request.FILES.getlist('files')
        use_baidu_ocr = request.POST.get('use_baidu_ocr') == 'on'
        # 当使用百度OCR时，自动启用强制OCR处理PDF

        
        if not uploaded_files:
            messages.error(request, '请选择要上传的文件')
            return redirect('invoice:invoice_recognize')
        
        recognition_ids = []
        successful_recognitions = []
        failed_recognitions = []
        auto_confirmed_count = 0
        
        # 批量处理上传的文件
        for uploaded_file in uploaded_files:
            try:
                # 创建识别记录
                recognition = InvoiceRecognition(
                    file=uploaded_file,
                    status='PROCESSING',
                    created_by=request.user
                )
                recognition.save()
                recognition_ids.append(recognition.pk)
                
                # 保存文件到临时目录
                file_path = os.path.join(settings.MEDIA_ROOT, recognition.file.name)
                
                # 识别发票
                invoice_info, text = InvoiceRecognizer.recognize_invoice(file_path, use_baidu_ocr)
                
                if invoice_info:
                    recognition.result = json.dumps(invoice_info, default=str)
                    recognition.status = 'COMPLETED'
                    recognition.save()
                    
                    # 检查识别结果是否完整，如果完整则自动确认
                    required_fields = ['invoice_number', 'amount', 'invoice_date']
                    is_complete = all(invoice_info.get(field) for field in required_fields)
                    
                    if is_complete:
                        # 信息完整，自动确认保存
                        try:
                            auto_confirmed_invoice = auto_confirm_recognition(recognition, request.user)
                            if auto_confirmed_invoice:
                                # 自动确认成功，增加计数器
                                auto_confirmed_count += 1
                                continue
                        except Exception as e:
                            logger.error(f"自动确认发票失败 {uploaded_file.name}: {str(e)}")
                    
                    # 信息不完整或自动确认失败，加入成功列表等待用户确认
                    successful_recognitions.append(recognition)
                else:
                    recognition.result = text or '识别失败'
                    recognition.status = 'FAILED'
                    recognition.save()
                    failed_recognitions.append({
                        'filename': uploaded_file.name,
                        'error': '无法识别发票信息'
                    })
                    
            except Exception as e:
                logger.error(f"发票识别失败 {uploaded_file.name}: {str(e)}")
                if 'recognition' in locals():
                    recognition.result = str(e)
                    recognition.status = 'FAILED'
                    recognition.save()
                failed_recognitions.append({
                    'filename': uploaded_file.name,
                    'error': str(e)
                })
        
        # 处理结果
        total_processed = auto_confirmed_count + len(successful_recognitions)
        
        # 显示处理结果消息
        if auto_confirmed_count > 0:
            messages.success(request, f'成功自动保存了 {auto_confirmed_count} 张发票（信息完整）')
        
        if successful_recognitions:
            # 有成功识别的发票，显示识别结果让用户确认
            messages.info(request, f'有 {len(successful_recognitions)} 张发票需要确认（信息不完整），请检查并确认识别结果')
            
            # 准备识别结果数据
            recognized_invoices = []
            for recognition in successful_recognitions:
                try:
                    invoice_info = json.loads(recognition.result)
                    recognized_invoices.append({
                        'recognition_id': recognition.pk,
                        'invoice_number': invoice_info.get('invoice_number', ''),
                        'amount': invoice_info.get('amount', 0),
                        'invoice_date': invoice_info.get('invoice_date', ''),
                        'seller_name': invoice_info.get('seller_name', ''),
                        'buyer_name': invoice_info.get('buyer_name', ''),
                        'confidence': invoice_info.get('confidence', 95),
                        'filename': os.path.basename(recognition.file.name) if recognition.file else '未知文件'
                    })
                except json.JSONDecodeError:
                    continue
            
            # 检查百度OCR配置状态
            from .baidu_ocr_config import BaiduOCRConfig
            
            # 获取当前用户的待确认识别记录
            pending_recognitions = InvoiceRecognition.objects.filter(
                status='COMPLETED',
                invoice__isnull=True,  # 未关联发票的记录
                created_by=request.user
            ).order_by('-created_at')
            
            context = {
                'baidu_ocr_configured': BaiduOCRConfig.is_configured(),
                'pending_recognitions': pending_recognitions,
                'recognized_invoices': recognized_invoices,
                'recognition_ids': ','.join(map(str, [r.pk for r in successful_recognitions]))
            }
            
            if failed_recognitions:
                messages.warning(request, f'有 {len(failed_recognitions)} 张发票识别失败')
            
            return render(request, 'invoice/invoice_recognize.html', context)
        
        elif auto_confirmed_count > 0 and not failed_recognitions:
            # 只有自动确认成功的发票，直接跳转回识别页面
            return redirect('invoice:invoice_recognize')
        
        elif failed_recognitions:
            # 全部失败的情况，进入手动填写页面
            failed_recognition_ids = []
            for recognition in InvoiceRecognition.objects.filter(status='FAILED', created_by=request.user).order_by('-created_at'):
                if recognition.pk in recognition_ids:
                    failed_recognition_ids.append(recognition.pk)
            if failed_recognition_ids:
                recognition_ids_str = ','.join(map(str, failed_recognition_ids))
                return redirect('invoice:manual_input', recognition_ids=recognition_ids_str)
        
        return redirect('invoice:invoice_recognize')
    
    # 检查百度OCR配置状态
    from .baidu_ocr_config import BaiduOCRConfig
    
    # 获取当前用户的待确认识别记录
    pending_recognitions = InvoiceRecognition.objects.filter(
        status='COMPLETED',
        invoice__isnull=True,  # 未关联发票的记录
        created_by=request.user
    ).order_by('-created_at')
    
    context = {
        'baidu_ocr_configured': BaiduOCRConfig.is_configured(),
        'pending_recognitions': pending_recognitions
    }
    return render(request, 'invoice/invoice_recognize.html', context)

# 发票识别确认视图
@login_required
def invoice_confirm(request, pk):
    recognition = get_object_or_404(InvoiceRecognition, pk=pk)
    
    if recognition.status != 'COMPLETED':
        messages.error(request, '发票识别未完成或失败')
        return redirect('invoice:invoice_recognize')
    
    try:
        invoice_info = json.loads(recognition.result)
    except json.JSONDecodeError:
        messages.error(request, '识别结果格式错误')
        return redirect('invoice:invoice_recognize')
    
    if request.method == 'POST':
        # 处理确认提交
        invoice_number = request.POST.get('invoice_number')
        invoice_content = request.POST.get('invoice_content')
        
        # 检查是否有重复发票（综合多个字段判断）
        seller_name = request.POST.get('seller_name')
        total_amount = request.POST.get('total_amount')
        invoice_date_str = request.POST.get('invoice_date')
        
        try:
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date() if invoice_date_str else None
        except ValueError:
            invoice_date = None
            
        if InvoiceValidator.check_duplicate(invoice_number, seller_name, total_amount, invoice_date):
            messages.error(request, '该发票已存在（发票号码、销售方、金额、日期匹配）')
            return redirect('invoice:invoice_confirm', pk=recognition.pk)
        
        try:
            # 创建发票对象
            invoice = Invoice(
                invoice_number=request.POST.get('invoice_number'),
                invoice_content=request.POST.get('invoice_content'),
                invoice_date=datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date(),
                invoice_type=request.POST.get('invoice_type'),
                amount=float(request.POST.get('amount')),
                tax_amount=float(request.POST.get('tax_amount') or 0),
                total_amount=float(request.POST.get('total_amount') or 0),
                seller_name=request.POST.get('seller_name'),
                seller_tax_id=request.POST.get('seller_tax_id'),
                buyer_name=request.POST.get('buyer_name'),
                buyer_tax_id=request.POST.get('buyer_tax_id'),
                description=request.POST.get('description'),
                created_by=request.user
            )
            
            category_id = request.POST.get('category')
            if category_id:
                invoice.category_id = category_id
            
            company_id = request.POST.get('company')
            if company_id:
                invoice.company_id = company_id
            
            # 使用识别记录中的文件
            invoice.file = recognition.file
            
            invoice.save()
            
            # 更新识别记录关联的发票
            recognition.invoice = invoice
            recognition.save()
            
            messages.success(request, '发票添加成功')
            return redirect('invoice:invoice_detail', pk=invoice.pk)
        except Exception as e:
            logger.error(f"确认发票失败: {str(e)}")
            messages.error(request, f'确认发票失败: {str(e)}')
            return redirect('invoice:invoice_confirm', pk=recognition.pk)
    
    # GET请求，显示确认表单
    categories = InvoiceCategory.objects.all()
    companies = Company.objects.all()
    context = {
        'recognition': recognition,
        'invoice_info': invoice_info,
        'categories': categories,
        'companies': companies,
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
    }
    return render(request, 'invoice/invoice_confirm.html', context)

# 批量发票确认视图
@login_required
def batch_confirm(request, recognition_ids):
    # 解析识别记录ID
    try:
        recognition_id_list = [int(id_str) for id_str in recognition_ids.split(',')]
    except ValueError:
        messages.error(request, '无效的识别记录ID')
        return redirect('invoice:invoice_recognize')
    
    # 获取识别记录
    recognitions = InvoiceRecognition.objects.filter(
        pk__in=recognition_id_list,
        status='COMPLETED',
        created_by=request.user
    )
    
    if not recognitions.exists():
        messages.error(request, '未找到有效的识别记录')
        return redirect('invoice:invoice_recognize')
    
    if request.method == 'POST':
        selected_recognition_ids = request.POST.getlist('recognition_ids')
        successful_saves = []
        failed_saves = []
        
        for recognition_id in selected_recognition_ids:
            try:
                recognition = recognitions.get(pk=recognition_id)
                invoice_info = json.loads(recognition.result)
                
                # 获取表单数据（使用recognition_id作为前缀）
                prefix = f'recognition_{recognition_id}_'
                invoice_number = request.POST.get(f'{prefix}invoice_number')
                
                # 获取其他字段用于重复检查
                seller_name = request.POST.get(f'{prefix}seller_name')
                total_amount = request.POST.get(f'{prefix}total_amount')
                invoice_date_str = request.POST.get(f'{prefix}invoice_date')
                
                try:
                    invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date() if invoice_date_str else None
                except ValueError:
                    invoice_date = None
                
                # 检查是否有重复发票（综合多个字段判断）
                if InvoiceValidator.check_duplicate(invoice_number, seller_name, total_amount, invoice_date):
                    failed_saves.append({
                        'filename': recognition.file.name,
                        'error': '该发票已存在（发票号码、销售方、金额、日期匹配）'
                    })
                    continue
                
                # 创建发票对象
                invoice = Invoice(
                    invoice_number=invoice_number,
                    invoice_content=request.POST.get(f'{prefix}invoice_content'),
                    invoice_date=datetime.strptime(request.POST.get(f'{prefix}invoice_date'), '%Y-%m-%d').date(),
                    invoice_type=request.POST.get(f'{prefix}invoice_type'),
                    amount=float(request.POST.get(f'{prefix}amount')),
                    tax_amount=float(request.POST.get(f'{prefix}tax_amount') or 0),
                    total_amount=float(request.POST.get(f'{prefix}total_amount') or 0),
                    seller_name=request.POST.get(f'{prefix}seller_name'),
                    seller_tax_id=request.POST.get(f'{prefix}seller_tax_id'),
                    buyer_name=request.POST.get(f'{prefix}buyer_name'),
                    buyer_tax_id=request.POST.get(f'{prefix}buyer_tax_id'),
                    description=request.POST.get(f'{prefix}description'),
                    created_by=request.user
                )
                
                category_id = request.POST.get(f'{prefix}category')
                if category_id:
                    invoice.category_id = category_id
                
                company_id = request.POST.get(f'{prefix}company')
                if company_id:
                    invoice.company_id = company_id
                
                # 使用识别记录中的文件
                invoice.file = recognition.file
                
                invoice.save()
                
                # 更新识别记录关联的发票
                recognition.invoice = invoice
                recognition.save()
                
                successful_saves.append(invoice)
                
            except Exception as e:
                logger.error(f"批量确认发票失败 {recognition_id}: {str(e)}")
                failed_saves.append({
                    'filename': recognition.file.name if 'recognition' in locals() else f'ID:{recognition_id}',
                    'error': str(e)
                })
        
        # 处理结果
        if successful_saves:
            messages.success(request, f'成功保存 {len(successful_saves)} 张发票')
        
        if failed_saves:
            error_messages = []
            for failed in failed_saves:
                error_messages.append(f"{failed['filename']}: {failed['error']}")
            messages.error(request, '以下发票保存失败:\n' + '\n'.join(error_messages))
        
        if successful_saves:
            return redirect('invoice:invoice_list')
        else:
            return redirect('invoice:invoice_recognize')
    
    # GET请求，显示批量确认表单
    recognition_data = []
    for recognition in recognitions:
        try:
            invoice_info = json.loads(recognition.result)
            recognition_data.append({
                'recognition': recognition,
                'invoice_info': invoice_info
            })
        except json.JSONDecodeError:
            continue
    
    categories = InvoiceCategory.objects.all()
    companies = Company.objects.all()
    context = {
        'recognition_data': recognition_data,
        'categories': categories,
        'companies': companies,
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
    }
    return render(request, 'invoice/batch_confirm.html', context)

# 发票类别管理视图
@login_required
def category_list(request):
    categories = InvoiceCategory.objects.all()
    context = {'categories': categories}
    return render(request, 'invoice/category_list.html', context)

@login_required
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, '请输入类别名称')
            return redirect('invoice:category_add')
        
        # 检查是否已存在同名类别
        if InvoiceCategory.objects.filter(name=name).exists():
            messages.error(request, '该类别名称已存在')
            return redirect('invoice:category_add')
        
        category = InvoiceCategory(name=name, description=description)
        category.save()
        messages.success(request, '类别添加成功')
        return redirect('invoice:category_list')
    
    return render(request, 'invoice/category_add.html')

@login_required
def category_edit(request, pk):
    category = get_object_or_404(InvoiceCategory, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, '请输入类别名称')
            return redirect('invoice:category_edit', pk=pk)
        
        # 检查是否已存在同名类别（排除当前编辑的类别）
        if InvoiceCategory.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, '该类别名称已存在')
            return redirect('invoice:category_edit', pk=pk)
        
        category.name = name
        category.description = description
        category.save()
        messages.success(request, '类别更新成功')
        return redirect('invoice:category_list')
    
    context = {'category': category}
    return render(request, 'invoice/category_edit.html', context)

@login_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(InvoiceCategory, pk=pk)
    
    # 检查是否有关联的发票
    if Invoice.objects.filter(category=category).exists():
        messages.error(request, '该类别下有关联的发票，无法删除')
        return redirect('invoice:category_list')
    
    category.delete()
    messages.success(request, '类别已删除')
    return redirect('invoice:category_list')



# 报告列表视图
@login_required
def report_list(request):
    # 暂时重定向到报告汇总页面
    return redirect('invoice:report_summary')

# 报告生成视图
@login_required
def report_generate(request):
    # 暂时重定向到报告汇总页面
    return redirect('invoice:report_summary')

# 统计报表视图
@login_required
def report_summary(request):
    # 获取筛选条件
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    company_id = request.GET.get('company')
    
    # 基础查询
    invoices = Invoice.objects.all()
    
    # 应用筛选条件
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            invoices = invoices.filter(invoice_date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            invoices = invoices.filter(invoice_date__lte=date_to)
        except ValueError:
            pass
    
    if category_id:
        invoices = invoices.filter(category_id=category_id)
    
    buyer_company = request.GET.get('buyer_company')
    if buyer_company:
        invoices = invoices.filter(buyer_name=buyer_company)
    
    # 统计数据
    total_count = invoices.count()
    total_amount = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 按类别统计
    from django.db.models import Q
    invoice_ids = list(invoices.values_list('id', flat=True))
    
    category_stats = InvoiceCategory.objects.annotate(
        invoice_count=Count('invoice', filter=Q(invoice__id__in=invoice_ids)),
        total_amount=Sum('invoice__total_amount', filter=Q(invoice__id__in=invoice_ids))
    )
    
    # 按购买方公司统计
    buyer_company_stats = invoices.values('buyer_name')\
                                 .annotate(
                                     invoice_count=Count('id'),
                                     total_amount=Sum('total_amount')
                                 )\
                                 .filter(buyer_name__isnull=False, buyer_name__gt='')\
                                 .order_by('-total_amount')
    
    # 按销售方统计
    seller_stats = invoices.values('seller_name')\
                          .annotate(
                              invoice_count=Count('id'),
                              total_amount=Sum('total_amount')
                          )\
                          .filter(seller_name__isnull=False, seller_name__gt='')\
                          .order_by('-total_amount')
    
    # 按购买方统计
    buyer_stats = invoices.values('buyer_name')\
                         .annotate(
                             invoice_count=Count('id'),
                             total_amount=Sum('total_amount')
                         )\
                         .filter(buyer_name__isnull=False, buyer_name__gt='')\
                         .order_by('-total_amount')
    
    # 按月份统计
    month_stats = invoices.extra(select={'month': "strftime('%%Y-%%m', invoice_date)"})\
                         .values('month')\
                         .annotate(count=Count('id'), total=Sum('total_amount'))\
                         .order_by('month')
    
    # 获取所有类别和购买方公司，用于筛选
    categories = InvoiceCategory.objects.all()
    # 获取所有购买方公司（从发票中的buyer_name去重）
    buyer_companies = Invoice.objects.values('buyer_name').distinct().exclude(buyer_name__isnull=True).exclude(buyer_name='').order_by('buyer_name')
    
    context = {
        'total_count': total_count,
        'total_amount': total_amount,
        'category_stats': category_stats,
        'buyer_company_stats': buyer_company_stats,
        'seller_stats': seller_stats,
        'buyer_stats': buyer_stats,
        'month_stats': month_stats,
        'categories': categories,
        'buyer_companies': buyer_companies,
        'date_from': date_from,
        'date_to': date_to,
        'selected_category': category_id,
        'selected_buyer_company': buyer_company,
    }
    return render(request, 'invoice/report_summary.html', context)

@login_required
def report_export(request):
    # 获取筛选条件
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    company_id = request.GET.get('company')
    
    # 基础查询
    invoices = Invoice.objects.all().order_by('-invoice_date')
    
    # 应用筛选条件
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            invoices = invoices.filter(invoice_date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            invoices = invoices.filter(invoice_date__lte=date_to)
        except ValueError:
            pass
    
    if category_id:
        invoices = invoices.filter(category_id=category_id)
    
    if company_id:
        invoices = invoices.filter(company_id=company_id)
    
    # 导出为CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    
    # 创建CSV写入器
    import csv
    writer = csv.writer(response)
    writer.writerow(['发票号码', '发票内容', '发票日期', '发票类型', '金额', '税额', '总金额', '销售方', '销售方税号', '购买方', '购买方税号', '类别', '公司', '描述'])
    
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.invoice_content,
            invoice.invoice_date,
            invoice.get_invoice_type_display(),
            invoice.amount,
            invoice.tax_amount,
            invoice.total_amount,
            invoice.seller_name,
            invoice.seller_tax_id,
            invoice.buyer_name,
            invoice.buyer_tax_id,
            invoice.category.name if invoice.category else '',
            invoice.company.name if invoice.company else '',
            invoice.description
        ])
    
    return response

# 批量删除发票视图
@login_required
@require_POST
def batch_delete(request):
    invoice_ids = request.POST.getlist('invoice_ids')
    
    if not invoice_ids:
        messages.error(request, '请选择要删除的发票')
        return redirect('invoice:invoice_list')
    
    try:
        # 获取要删除的发票
        invoices = Invoice.objects.filter(id__in=invoice_ids)
        deleted_count = invoices.count()
        
        if deleted_count == 0:
            messages.error(request, '未找到要删除的发票')
            return redirect('invoice:invoice_list')
        
        # 执行删除操作
        invoices.delete()
        
        messages.success(request, f'成功删除 {deleted_count} 张发票')
        logger.info(f"用户 {request.user.username} 批量删除了 {deleted_count} 张发票，ID: {invoice_ids}")
        
    except Exception as e:
        logger.error(f"批量删除发票失败: {str(e)}")
        messages.error(request, f'删除发票失败: {str(e)}')
    
    return redirect('invoice:invoice_list')
