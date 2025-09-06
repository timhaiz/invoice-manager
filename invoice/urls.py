from django.urls import path
from . import views

app_name = 'invoice'

urlpatterns = [
    path('', views.index, name='index'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/add/', views.invoice_add, name='invoice_add'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/batch-delete/', views.batch_delete, name='batch_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('reports/', views.report_list, name='report_list'),
    path('reports/summary/', views.report_summary, name='report_summary'),
    path('reports/generate/', views.report_generate, name='report_generate'),
    path('reports/export/', views.report_export, name='report_export'),

    path('recognize/', views.invoice_recognize, name='invoice_recognize'),
    path('recognize/confirm/<int:pk>/', views.invoice_confirm, name='invoice_confirm'),
    path('recognize/batch-confirm/<str:recognition_ids>/', views.batch_confirm, name='batch_confirm'),
    path('recognize/manual-input/<str:recognition_ids>/', views.manual_input, name='manual_input'),
    
    # 文件下载相关URL
    path('download/<int:pk>/', views.download_invoice_file, name='download_invoice_file'),
    path('batch-download/', views.batch_download_invoice_files, name='batch_download_invoice_files'),
]