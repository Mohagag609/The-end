from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
import csv
from decimal import Decimal
from datetime import datetime

from projects.models import Project, Stage
from partners.models import Partner, ProjectPartner, Voucher
from suppliers.models import Supplier
from purchases.models import PurchaseInvoice, PurchaseItem
from expenses.models import Expense
from inventory.models import Item, StockMove
from allocations.models import Allocation
from settlements.models import PartnerSettleBatch

def reports_index(request, project_id):
    """صفحة التقارير الرئيسية"""
    project = get_object_or_404(Project, id=project_id)
    
    context = {
        'project': project,
    }
    
    return render(request, 'reports/index.html', context)

def partners_report(request, project_id):
    """تقرير كشف حساب الشركاء"""
    project = get_object_or_404(Project, id=project_id)
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    report_data = []
    totals = {
        'deposits': Decimal('0.00'),
        'withdrawals': Decimal('0.00'),
        'wallet_balance': Decimal('0.00'),
        'carry_forward': Decimal('0.00'),
    }
    
    for partner in partners:
        deposits = partner.get_total_receipts()
        withdrawals = partner.get_total_payments()
        
        data = {
            'partner': partner,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'wallet_balance': partner.wallet_balance,
            'carry_forward': partner.carry_forward,
            'net_balance': partner.wallet_balance + partner.carry_forward,
        }
        
        report_data.append(data)
        
        totals['deposits'] += deposits
        totals['withdrawals'] += withdrawals
        totals['wallet_balance'] += partner.wallet_balance
        totals['carry_forward'] += partner.carry_forward
    
    totals['net_balance'] = totals['wallet_balance'] + totals['carry_forward']
    
    context = {
        'project': project,
        'report_data': report_data,
        'totals': totals,
    }
    
    return render(request, 'reports/partners.html', context)

def suppliers_report(request, project_id=None):
    """تقرير كشف حساب الموردين"""
    project = None
    if project_id:
        project = get_object_or_404(Project, id=project_id)
    
    suppliers = Supplier.objects.filter(is_active=True)
    
    report_data = []
    totals = {
        'purchases': Decimal('0.00'),
        'payments': Decimal('0.00'),
        'discounts': Decimal('0.00'),
        'balance': Decimal('0.00'),
    }
    
    for supplier in suppliers:
        purchases = supplier.get_total_purchases(project)
        payments = supplier.get_total_payments(project)
        discounts = supplier.get_total_discounts(project)
        balance = supplier.get_balance(project)
        
        data = {
            'supplier': supplier,
            'purchases': purchases,
            'payments': payments,
            'discounts': discounts,
            'balance': balance,
        }
        
        report_data.append(data)
        
        totals['purchases'] += purchases
        totals['payments'] += payments
        totals['discounts'] += discounts
        totals['balance'] += balance
    
    context = {
        'project': project,
        'report_data': report_data,
        'totals': totals,
    }
    
    return render(request, 'reports/suppliers.html', context)

def iron_report(request, project_id):
    """تقرير كشف حساب الحديد"""
    project = get_object_or_404(Project, id=project_id)
    
    # الحصول على فئة الحديد
    from inventory.models import ItemCategory
    iron_category = ItemCategory.objects.filter(name__icontains='حديد').first()
    
    if not iron_category:
        messages.warning(request, 'لا توجد فئة للحديد في النظام')
        return redirect('reports:index', project_id=project.id)
    
    # بنود فواتير الشراء للحديد
    iron_items = PurchaseItem.objects.filter(
        invoice__project=project,
        invoice__status='posted',
        item__category=iron_category
    ).select_related('item', 'invoice__supplier')
    
    # تجميع البيانات
    by_item = {}
    for purchase_item in iron_items:
        item_key = purchase_item.item.id
        
        if item_key not in by_item:
            by_item[item_key] = {
                'item': purchase_item.item,
                'purchases': [],
                'total_qty': Decimal('0.000'),
                'total_amount': Decimal('0.00'),
            }
        
        by_item[item_key]['purchases'].append({
            'date': purchase_item.invoice.date,
            'supplier': purchase_item.invoice.supplier.name,
            'invoice_no': purchase_item.invoice.invoice_no,
            'qty': purchase_item.qty,
            'unit_cost': purchase_item.unit_cost,
            'total': purchase_item.line_total,
        })
        
        by_item[item_key]['total_qty'] += purchase_item.qty
        by_item[item_key]['total_amount'] += purchase_item.line_total
    
    # المجاميع الكلية
    grand_total_qty = sum(item['total_qty'] for item in by_item.values())
    grand_total_amount = sum(item['total_amount'] for item in by_item.values())
    
    context = {
        'project': project,
        'by_item': by_item.values(),
        'grand_total_qty': grand_total_qty,
        'grand_total_amount': grand_total_amount,
    }
    
    return render(request, 'reports/iron.html', context)

def export_csv(request, project_id):
    """تصدير التقارير إلى CSV"""
    project = get_object_or_404(Project, id=project_id)
    report_type = request.GET.get('type', 'partners')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{project.code}_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    # إضافة BOM لدعم Excel مع UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if report_type == 'partners':
        # تقرير الشركاء
        writer.writerow(['الشريك', 'النسبة %', 'الإيداعات', 'السحوبات', 'رصيد المحفظة', 'المرحّل', 'الصافي'])
        
        partners = ProjectPartner.objects.filter(project=project).select_related('partner')
        for partner in partners:
            writer.writerow([
                partner.partner.name,
                partner.share_pct,
                partner.get_total_receipts(),
                partner.get_total_payments(),
                partner.wallet_balance,
                partner.carry_forward,
                partner.wallet_balance + partner.carry_forward
            ])
    
    elif report_type == 'expenses':
        # تقرير المصروفات
        writer.writerow(['التاريخ', 'المرحلة', 'الفئة', 'المستفيد', 'البيان', 'المبلغ'])
        
        expenses = Expense.objects.filter(project=project).order_by('-date')
        for expense in expenses:
            writer.writerow([
                expense.date,
                expense.stage.name if expense.stage else '',
                expense.get_category_display(),
                expense.get_payee_display(),
                expense.description,
                expense.amount
            ])
    
    elif report_type == 'purchases':
        # تقرير المشتريات
        writer.writerow(['التاريخ', 'المورد', 'رقم الفاتورة', 'الصنف', 'الكمية', 'السعر', 'الإجمالي'])
        
        items = PurchaseItem.objects.filter(
            invoice__project=project,
            invoice__status='posted'
        ).select_related('item', 'invoice__supplier')
        
        for item in items:
            writer.writerow([
                item.invoice.date,
                item.invoice.supplier.name,
                item.invoice.invoice_no,
                item.item.name,
                item.qty,
                item.unit_cost,
                item.line_total
            ])
    
    elif report_type == 'stock':
        # تقرير حركات المخزون
        writer.writerow(['التاريخ', 'المخزن', 'الصنف', 'النوع', 'وارد', 'صادر', 'القيمة', 'المرحلة'])
        
        moves = StockMove.objects.filter(project=project).order_by('-move_date')
        for move in moves:
            writer.writerow([
                move.move_date,
                move.warehouse.name,
                move.item.name,
                move.get_ref_type_display(),
                move.qty_in,
                move.qty_out,
                move.amount,
                move.stage.name if move.stage else ''
            ])
    
    return response