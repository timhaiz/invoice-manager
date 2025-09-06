// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 自动隐藏警告消息
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // 文件上传预览 - 支持单文件和多文件上传
    const fileInput = document.getElementById('id_file') || document.getElementById('id_files');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                const fileNameElement = document.getElementById('file-name');
                const filePreviewElement = document.getElementById('file-preview');
                if (fileNameElement) {
                    fileNameElement.textContent = fileName;
                }
                if (filePreviewElement) {
                    filePreviewElement.classList.remove('d-none');
                }
            }
        });
    }

    // 拖放上传区域
    const uploadArea = document.querySelector('.upload-area');
    if (uploadArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight() {
            uploadArea.classList.add('bg-light');
        }

        function unhighlight() {
            uploadArea.classList.remove('bg-light');
        }

        uploadArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        }

        uploadArea.addEventListener('click', function() {
            if (fileInput) {
                fileInput.click();
            }
        });
    }

    // 确认删除对话框
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('确定要删除这条记录吗？此操作不可撤销。')) {
                e.preventDefault();
            }
        });
    });

    // 日期选择器初始化
    const dateInputs = document.querySelectorAll('.datepicker');
    if (dateInputs.length > 0) {
        dateInputs.forEach(input => {
            input.setAttribute('type', 'date');
        });
    }

    // 发票选择功能（用于创建报销单）
    const invoiceCheckboxes = document.querySelectorAll('.invoice-checkbox');
    const selectedInvoicesInput = document.getElementById('selected_invoices');
    const totalAmountElement = document.getElementById('total_amount');
    
    if (invoiceCheckboxes.length > 0 && selectedInvoicesInput && totalAmountElement) {
        invoiceCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateSelectedInvoices);
        });

        function updateSelectedInvoices() {
            const selectedIds = [];
            let totalAmount = 0;
            
            invoiceCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    selectedIds.push(checkbox.value);
                    totalAmount += parseFloat(checkbox.dataset.amount || 0);
                }
            });
            
            selectedInvoicesInput.value = selectedIds.join(',');
            totalAmountElement.textContent = totalAmount.toFixed(2);
        }
    }

    // 报表日期范围选择器
    const startDateInput = document.getElementById('date_from');
    const endDateInput = document.getElementById('date_to');
    
    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', function() {
            endDateInput.min = startDateInput.value;
        });
        
        endDateInput.addEventListener('change', function() {
            startDateInput.max = endDateInput.value;
        });
    }

    // 表格排序功能
    const sortableHeaders = document.querySelectorAll('th.sortable');
    if (sortableHeaders.length > 0) {
        sortableHeaders.forEach(header => {
            header.addEventListener('click', function() {
                const field = this.dataset.field;
                let order = this.dataset.order || 'asc';
                
                // 切换排序顺序
                order = order === 'asc' ? 'desc' : 'asc';
                this.dataset.order = order;
                
                // 更新URL参数并重新加载页面
                const url = new URL(window.location.href);
                url.searchParams.set('sort', field);
                url.searchParams.set('order', order);
                window.location.href = url.toString();
            });
        });
    }

    // 发票识别结果确认页面功能已移至各自页面的JavaScript中

    // 打印功能
    const printBtn = document.getElementById('print-btn');
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }
});