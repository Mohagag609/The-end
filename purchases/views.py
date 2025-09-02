from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q, Count
from decimal import Decimal
from datetime import datetime

from .models import PurchaseInvoice, PurchaseItem
from projects.models import Project
from suppliers.models import Supplier
from inventory.models import Item

def purchases_list(request, project_id):
    """قائمة فواتير الشراء"""
    project = get_object_or_404(Project, id=project_id)
    
    invoices = PurchaseInvoice.objects.filter(
        project=project
    ).select_related('supplier').order_by('-date', '-created_at')
    
    # فلترة
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        invoices = invoices.filter(supplier_id=supplier_id)
    
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    
    # المجاميع
    totals = invoices.aggregate(
        count=Count('id'),
        total=Sum('total'),
        tax=Sum('tax_amount'),
        discount=Sum('discount_amount')
    )
    
    suppliers = Supplier.objects.filter(is_active=True)
    
    context = {
        'project': project,
        'invoices': invoices[:50],  # عرض أول 50 فاتورة
        'suppliers': suppliers,
        'totals': totals,
        'filters': {
            'supplier': supplier_id,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'purchases/list.html', context)

def create_purchase(request, project_id):
    """إنشاء فاتورة شراء"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id')
        invoice_no = request.POST.get('invoice_no')
        date = request.POST.get('date', datetime.now().date())
        notes = request.POST.get('notes', '')
        
        supplier = get_object_or_404(Supplier, id=supplier_id)
        
        # التحقق من عدم تكرار رقم الفاتورة
        if PurchaseInvoice.objects.filter(
            project=project,
            supplier=supplier,
            invoice_no=invoice_no
        ).exists():
            messages.error(request, 'رقم الفاتورة موجود بالفعل لهذا المورد')
            return redirect('purchases:list', project_id=project.id)
        
        # إنشاء الفاتورة
        invoice = PurchaseInvoice.objects.create(
            project=project,
            supplier=supplier,
            invoice_no=invoice_no,
            date=date,
            notes=notes,
            status='draft'
        )
        
        # Handle attachment
        if request.FILES.get('attachment'):
            invoice.attachment = request.FILES['attachment']
            invoice.save()
        
        # إضافة البنود
        item_ids = request.POST.getlist('item_id[]')
        quantities = request.POST.getlist('qty[]')
        unit_costs = request.POST.getlist('unit_cost[]')
        tax_rates = request.POST.getlist('tax_rate[]')
        
        for i in range(len(item_ids)):
            if item_ids[i]:
                item = get_object_or_404(Item, id=item_ids[i])
                qty = Decimal(quantities[i] or '0')
                unit_cost = Decimal(unit_costs[i] or '0')
                tax_rate = Decimal(tax_rates[i] or '0')
                
                if qty > 0 and unit_cost > 0:
                    PurchaseItem.objects.create(
                        invoice=invoice,
                        item=item,
                        qty=qty,
                        unit_cost=unit_cost,
                        tax_rate=tax_rate
                    )
        
        # حساب المجاميع
        invoice.calculate_totals()
        
        # ترحيل الفاتورة إذا طُلب ذلك
        if request.POST.get('post_invoice') == 'on':
            try:
                invoice.post()
                messages.success(request, f'تم ترحيل الفاتورة {invoice_no} بنجاح')
            except Exception as e:
                messages.warning(request, f'تم إنشاء الفاتورة ولكن فشل الترحيل: {str(e)}')
        else:
            messages.success(request, f'تم إنشاء الفاتورة {invoice_no} كمسودة')
        
        return redirect('purchases:invoice_detail', project_id=project.id, invoice_id=invoice.id)
    
    suppliers = Supplier.objects.filter(is_active=True)
    items = Item.objects.filter(is_active=True).select_related('category')
    
    context = {
        'project': project,
        'suppliers': suppliers,
        'items': items,
        'today': datetime.now().date()
    }
    
    return render(request, 'purchases/create.html', context)

def invoice_detail(request, project_id, invoice_id):
    """تفاصيل الفاتورة"""
    project = get_object_or_404(Project, id=project_id)
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id, project=project)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'post' and invoice.status == 'draft':
            try:
                invoice.post()
                messages.success(request, 'تم ترحيل الفاتورة بنجاح')
            except Exception as e:
                messages.error(request, str(e))
        
        elif action == 'cancel' and invoice.status == 'posted':
            try:
                invoice.cancel()
                messages.success(request, 'تم إلغاء الفاتورة')
            except Exception as e:
                messages.error(request, str(e))
        
        return redirect('purchases:invoice_detail', project_id=project.id, invoice_id=invoice.id)
    
    items = invoice.items.all().select_related('item__category')
    
    context = {
        'project': project,
        'invoice': invoice,
        'items': items,
    }
    
    return render(request, 'purchases/invoice_detail.html', context)