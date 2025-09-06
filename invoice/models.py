from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import os

# 公司信息模型
class Company(models.Model):
    name = models.CharField('公司名称', max_length=100)
    tax_id = models.CharField('税号', max_length=50, unique=True)
    address = models.CharField('地址', max_length=200, blank=True, null=True)
    phone = models.CharField('电话', max_length=20, blank=True, null=True)
    bank_name = models.CharField('开户行', max_length=100, blank=True, null=True)
    bank_account = models.CharField('银行账号', max_length=50, blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '公司信息'
        verbose_name_plural = '公司信息'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

# 发票类别模型
class InvoiceCategory(models.Model):
    name = models.CharField('类别名称', max_length=50)
    description = models.TextField('描述', blank=True, null=True)
    monthly_limit = models.DecimalField('月度限额', max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '发票类别'
        verbose_name_plural = '发票类别'
        ordering = ['name']
    
    def __str__(self):
        return self.name

# 发票模型
class Invoice(models.Model):
    INVOICE_TYPE_CHOICES = (
        ('VAT_SPECIAL', '增值税专用发票'),
        ('VAT_GENERAL', '增值税普通发票'),
        ('ELECTRONIC', '电子发票'),
        ('PAPER', '纸质发票'),
        ('OTHER', '其他'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', '待处理'),
        ('VERIFIED', '已验证'),
        ('REJECTED', '已拒绝'),
        ('USED', '已使用'),
    )
    
    invoice_number = models.CharField('发票号码', max_length=50, unique=True)
    invoice_content = models.CharField('发票内容', max_length=200, blank=True, null=True)  # 原发票代码字段
    invoice_date = models.DateField('开票日期')
    invoice_type = models.CharField('发票类型', max_length=20, choices=INVOICE_TYPE_CHOICES)
    amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField('税额', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('价税合计', max_digits=10, decimal_places=2)
    seller_name = models.CharField('销售方名称', max_length=100)
    seller_tax_id = models.CharField('销售方税号', max_length=50)
    buyer_name = models.CharField('购买方名称', max_length=100)
    buyer_tax_id = models.CharField('购买方税号', max_length=50)
    category = models.ForeignKey(InvoiceCategory, on_delete=models.SET_NULL, null=True, verbose_name='发票类别')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, verbose_name='所属公司')
    description = models.TextField('描述', blank=True, null=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_verified = models.BooleanField('是否已验证', default=False)
    verification_date = models.DateTimeField('验证时间', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invoices', verbose_name='创建人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    def invoice_file_path(instance, filename):
        # 文件将上传到 MEDIA_ROOT/invoices/年月/发票号码_文件名
        ext = filename.split('.')[-1]
        new_filename = f"{instance.invoice_number}.{ext}"
        return os.path.join('invoices', timezone.now().strftime('%Y%m'), new_filename)
    
    file = models.FileField('发票文件', upload_to=invoice_file_path, blank=True, null=True)
    image = models.ImageField('发票图片', upload_to=invoice_file_path, blank=True, null=True)
    
    class Meta:
        verbose_name = '发票'
        verbose_name_plural = '发票'
        ordering = ['-invoice_date', '-created_at']
    
    def __str__(self):
        return f"{self.invoice_number} - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.amount + self.tax_amount
        super().save(*args, **kwargs)



def invoice_recognition_file_path(instance, filename):
    # 文件将上传到 MEDIA_ROOT/invoice_files/年月日/原始文件名
    return os.path.join('invoice_files', timezone.now().strftime('%Y%m%d'), filename)

# 发票识别记录
class InvoiceRecognition(models.Model):
    STATUS_CHOICES = (
        ('PENDING', '待处理'),
        ('PROCESSING', '处理中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
        ('MANUAL_COMPLETED', '手动完成'),
    )
    
    file = models.FileField('文件', upload_to=invoice_recognition_file_path)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    result = models.TextField('识别结果', blank=True, null=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='recognitions', verbose_name='关联发票')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recognitions', verbose_name='创建人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '发票识别记录'
        verbose_name_plural = '发票识别记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"识别记录 {self.id}"
