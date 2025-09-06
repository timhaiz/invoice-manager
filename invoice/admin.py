from django.contrib import admin
from .models import Company, InvoiceCategory, Invoice, InvoiceRecognition

# 公司信息管理
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'phone', 'created_at')
    search_fields = ('name', 'tax_id')
    list_filter = ('created_at',)

# 发票类别管理
@admin.register(InvoiceCategory)
class InvoiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_limit', 'created_at')
    search_fields = ('name',)

# 发票管理
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'invoice_content', 'invoice_date', 'invoice_type', 
                    'total_amount', 'seller_name', 'buyer_name', 'category', 'status', 'is_verified')
    list_filter = ('invoice_date', 'invoice_type', 'status', 'is_verified', 'category', 'company')
    search_fields = ('invoice_number', 'invoice_content', 'seller_name', 'buyer_name')
    date_hierarchy = 'invoice_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('invoice_number', 'invoice_content', 'invoice_date', 'invoice_type')
        }),
        ('金额信息', {
            'fields': ('amount', 'tax_amount', 'total_amount')
        }),
        ('销售方信息', {
            'fields': ('seller_name', 'seller_tax_id')
        }),
        ('购买方信息', {
            'fields': ('buyer_name', 'buyer_tax_id', 'company')
        }),
        ('分类信息', {
            'fields': ('category', 'description')
        }),
        ('状态信息', {
            'fields': ('status', 'is_verified', 'verification_date')
        }),
        ('文件信息', {
            'fields': ('file', 'image')
        }),
        ('其他信息', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )



# 发票识别记录管理
@admin.register(InvoiceRecognition)
class InvoiceRecognitionAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'status', 'invoice', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
