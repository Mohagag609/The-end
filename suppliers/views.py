from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal

from .models import Supplier, SupplierPayment, SupplierDiscount

def suppliers_list(request):
    """قائمة الموردين"""
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    for supplier in suppliers:
        supplier.total_purchases = supplier.get_total_purchases()
        supplier.total_payments = supplier.get_total_payments()
        supplier.balance = supplier.get_balance()
    
    context = {
        'suppliers': suppliers,
    }
    
    return render(request, 'suppliers/list.html', context)

def create_supplier(request):
    """إنشاء مورد جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        tax_number = request.POST.get('tax_number', '')
        
        supplier = Supplier.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address,
            tax_number=tax_number
        )
        
        messages.success(request, f'تم إنشاء المورد {name} بنجاح')
        return redirect('suppliers:list')
    
    return render(request, 'suppliers/create.html')

def supplier_detail(request, supplier_id):
    """تفاصيل المورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # الفواتير
    from purchases.models import PurchaseInvoice
    invoices = PurchaseInvoice.objects.filter(
        supplier=supplier,
        status='posted'
    ).order_by('-date')[:20]
    
    # المدفوعات
    payments = SupplierPayment.objects.filter(
        supplier=supplier,
        status='posted'
    ).order_by('-payment_date')[:20]
    
    # الخصومات
    discounts = SupplierDiscount.objects.filter(
        supplier=supplier
    ).order_by('-date')[:10]
    
    context = {
        'supplier': supplier,
        'invoices': invoices,
        'payments': payments,
        'discounts': discounts,
        'total_purchases': supplier.get_total_purchases(),
        'total_payments': supplier.get_total_payments(),
        'total_discounts': supplier.get_total_discounts(),
        'balance': supplier.get_balance(),
    }
    
    return render(request, 'suppliers/detail.html', context)

def supplier_statement(request, supplier_id):
    """كشف حساب المورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # جمع كل المعاملات
    transactions = []
    
    # الفواتير
    from purchases.models import PurchaseInvoice
    invoices = PurchaseInvoice.objects.filter(
        supplier=supplier,
        status='posted'
    )
    
    for invoice in invoices:
        transactions.append({
            'date': invoice.date,
            'type': 'فاتورة',
            'ref': invoice.invoice_no,
            'debit': invoice.total,
            'credit': Decimal('0.00'),
            'description': f'فاتورة شراء - {invoice.project.name}'
        })
    
    # المدفوعات
    payments = SupplierPayment.objects.filter(
        supplier=supplier,
        status='posted'
    )
    
    for payment in payments:
        transactions.append({
            'date': payment.payment_date,
            'type': 'دفعة',
            'ref': payment.reference or '',
            'debit': Decimal('0.00'),
            'credit': payment.amount,
            'description': payment.notes or 'دفعة للمورد'
        })
    
    # الخصومات
    discounts = SupplierDiscount.objects.filter(supplier=supplier)
    
    for discount in discounts:
        transactions.append({
            'date': discount.date,
            'type': 'خصم',
            'ref': '',
            'debit': Decimal('0.00'),
            'credit': discount.amount,
            'description': discount.reason
        })
    
    # ترتيب حسب التاريخ
    transactions.sort(key=lambda x: x['date'])
    
    # حساب الرصيد التراكمي
    balance = Decimal('0.00')
    for trans in transactions:
        balance += trans['debit'] - trans['credit']
        trans['balance'] = balance
    
    context = {
        'supplier': supplier,
        'transactions': transactions,
        'final_balance': balance,
    }
    
    return render(request, 'suppliers/statement.html', context)