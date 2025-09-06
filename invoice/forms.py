from django import forms
from django.core.exceptions import ValidationError
from .models import Invoice, InvoiceCategory, Company
from .utils import InvoiceValidator

class InvoiceForm(forms.ModelForm):
    """发票表单"""
    
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'invoice_content', 'invoice_date', 'invoice_type',
            'amount', 'tax_amount', 'total_amount', 'seller_name', 'seller_tax_id',
            'buyer_name', 'buyer_tax_id', 'category', 'company', 'description',
            'file', 'image'
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'invoice_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_content': forms.TextInput(attrs={'class': 'form-control'}),
            'seller_name': forms.TextInput(attrs={'class': 'form-control'}),
            'seller_tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'buyer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'buyer_tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': '.jpg,.jpeg,.png'}),
        }
        labels = {
            'invoice_number': '发票号码',
            'invoice_content': '发票内容',
            'invoice_date': '开票日期',
            'invoice_type': '发票类型',
            'amount': '金额',
            'tax_amount': '税额',
            'total_amount': '价税合计',
            'seller_name': '销售方名称',
            'seller_tax_id': '销售方税号',
            'buyer_name': '购买方名称',
            'buyer_tax_id': '购买方税号',
            'category': '发票类别',
            'company': '所属公司',
            'description': '备注',
            'file': '发票文件',
            'image': '发票图片',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置必填字段
        self.fields['invoice_number'].required = True
        self.fields['invoice_content'].required = True
        self.fields['invoice_date'].required = True
        self.fields['amount'].required = True
        
        # 设置选择字段的查询集
        self.fields['category'].queryset = InvoiceCategory.objects.all()
        self.fields['company'].queryset = Company.objects.all()
        
        # 设置空选项
        self.fields['category'].empty_label = "请选择类别"
        self.fields['company'].empty_label = "请选择公司"
    
    def clean_invoice_number(self):
        """验证发票号码"""
        invoice_number = self.cleaned_data.get('invoice_number')
        if invoice_number and not InvoiceValidator.validate_invoice_number(invoice_number):
            raise ValidationError('发票号码格式不正确')
        return invoice_number
    
    def clean_invoice_content(self):
        """验证发票内容"""
        invoice_content = self.cleaned_data.get('invoice_content')
        # 发票内容不需要严格的格式验证，只需要基本的长度检查
        if invoice_content and len(invoice_content.strip()) < 2:
            raise ValidationError('发票内容不能为空或过短')
        return invoice_content
    
    def clean(self):
        """表单整体验证"""
        cleaned_data = super().clean()
        invoice_number = cleaned_data.get('invoice_number')
        invoice_content = cleaned_data.get('invoice_content')
        amount = cleaned_data.get('amount')
        tax_amount = cleaned_data.get('tax_amount', 0)
        total_amount = cleaned_data.get('total_amount')
        
        # 检查重复发票（仅在新建时，只检查发票号码）
        if not self.instance.pk and invoice_number:
            if InvoiceValidator.check_duplicate(invoice_number):
                raise ValidationError('该发票号码已存在')
        
        # 验证金额计算
        if amount is not None and tax_amount is not None:
            calculated_total = amount + tax_amount
            if total_amount is None:
                cleaned_data['total_amount'] = calculated_total
            elif abs(total_amount - calculated_total) > 0.01:  # 允许小数点误差
                raise ValidationError('价税合计应等于金额加税额')
        
        return cleaned_data