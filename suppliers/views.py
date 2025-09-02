from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import datetime

from .models import Supplier, SupplierPayment, SupplierDiscount
from purchases.models import PurchaseInvoice
from projects.models import Project

def suppliers_list(request):
    """قائمة الموردين"""
    suppliers = Supplier.objects.filter(is_active=True)
    
    # حساب الأرصدة لكل مورد
    totals = {
        'purchases': Decimal('0'),
        'payments': Decimal('0'),
        'balance': Decimal('0'),
    }
    
    for supplier in suppliers:
        # إجمالي المشتريات
        purchases = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status='posted'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # إجمالي المدفوعات
        payments = SupplierPayment.objects.filter(
            supplier=supplier
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        supplier.total_purchases = purchases
        supplier.total_payments = payments
        supplier.balance = purchases - payments
        
        totals['purchases'] += purchases
        totals['payments'] += payments
        totals['balance'] += supplier.balance
    
    context = {
        'suppliers': suppliers,
        'totals': totals,
    }
    
    return render(request, 'suppliers/list.html', context)

def create_supplier(request):
    """إضافة مورد جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        type = request.POST.get('type', 'materials')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        
        # توليد كود تلقائي إذا لم يُدخل
        if not code:
            last_supplier = Supplier.objects.order_by('-id').first()
            if last_supplier:
                code = f'SUP{last_supplier.id + 1:04d}'
            else:
                code = 'SUP0001'
        
        # التحقق من عدم تكرار الكود
        if Supplier.objects.filter(code=code).exists():
            messages.error(request, f'كود المورد {code} موجود بالفعل')
            return redirect('suppliers:list')
        
        supplier = Supplier.objects.create(
            name=name,
            code=code,
            type=type,
            phone=phone,
            email=email,
            address=address
        )
        
        messages.success(request, f'تم إضافة المورد "{name}" بنجاح')
        return redirect('suppliers:list')
    
    return redirect('suppliers:list')

def supplier_detail(request, supplier_id):
    """تفاصيل المورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # الفواتير
    invoices = PurchaseInvoice.objects.filter(
        supplier=supplier
    ).order_by('-date')[:10]
    
    # المدفوعات
    payments = SupplierPayment.objects.filter(
        supplier=supplier
    ).order_by('-date')[:10]
    
    # الخصومات
    discounts = SupplierDiscount.objects.filter(
        supplier=supplier
    ).order_by('-date')[:10]
    
    context = {
        'supplier': supplier,
        'invoices': invoices,
        'payments': payments,
        'discounts': discounts,
    }
    
    return render(request, 'suppliers/detail.html', context)

def supplier_statement(request, supplier_id):
    """كشف حساب المورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # جميع المعاملات
    transactions = []
    
    # الفواتير
    invoices = PurchaseInvoice.objects.filter(
        supplier=supplier,
        status='posted'
    )
    for invoice in invoices:
        transactions.append({
            'date': invoice.date,
            'type': 'invoice',
            'ref': invoice.invoice_no,
            'description': f'فاتورة شراء',
            'debit': invoice.total_amount,
            'credit': Decimal('0'),
        })
    
    # المدفوعات
    payments = SupplierPayment.objects.filter(supplier=supplier)
    for payment in payments:
        transactions.append({
            'date': payment.date,
            'type': 'payment',
            'ref': payment.ref_no,
            'description': payment.description,
            'debit': Decimal('0'),
            'credit': payment.amount,
        })
    
    # الخصومات
    discounts = SupplierDiscount.objects.filter(supplier=supplier)
    for discount in discounts:
        transactions.append({
            'date': discount.date,
            'type': 'discount',
            'ref': f'خصم',
            'description': discount.description,
            'debit': Decimal('0'),
            'credit': discount.amount,
        })
    
    # ترتيب حسب التاريخ
    transactions.sort(key=lambda x: x['date'])
    
    # حساب الرصيد التراكمي
    balance = Decimal('0')
    for trans in transactions:
        balance += trans['debit'] - trans['credit']
        trans['balance'] = balance
    
    context = {
        'supplier': supplier,
        'transactions': transactions,
        'final_balance': balance,
    }
    
    return render(request, 'suppliers/statement.html', context)

def supplier_payment(request, supplier_id):
    """دفعة للمورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        date = request.POST.get('date', datetime.now().date())
        payment_method = request.POST.get('payment_method', 'cash')
        ref_no = request.POST.get('ref_no', '')
        description = request.POST.get('description', '')
        
        payment = SupplierPayment.objects.create(
            supplier=supplier,
            amount=amount,
            date=date,
            payment_method=payment_method,
            ref_no=ref_no,
            description=description
        )
        
        messages.success(request, f'تم تسجيل دفعة بقيمة {amount} ج.م للمورد {supplier.name}')
        return redirect('suppliers:detail', supplier_id=supplier.id)
    
    # حساب الرصيد المستحق
    purchases = PurchaseInvoice.objects.filter(
        supplier=supplier,
        status='posted'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    payments = SupplierPayment.objects.filter(
        supplier=supplier
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    balance = purchases - payments
    
    context = {
        'supplier': supplier,
        'balance': balance,
        'today': datetime.now().date(),
    }
    
    return render(request, 'suppliers/payment.html', context)