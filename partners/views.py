from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import JsonResponse
from decimal import Decimal
from datetime import datetime

from .models import Partner, ProjectPartner, Voucher, WalletPriority
from projects.models import Project

def partners_list(request, project_id):
    """قائمة الشركاء في المشروع"""
    project = get_object_or_404(Project, id=project_id)
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    total_shares = partners.aggregate(total=Sum('share_pct'))['total'] or Decimal('0.00')
    shares_valid = total_shares == Decimal('100.00')
    
    total_deposits = Decimal('0.00')
    total_withdrawals = Decimal('0.00')
    total_balance = Decimal('0.00')
    
    for partner in partners:
        partner.deposits = partner.get_total_receipts()
        partner.withdrawals = partner.get_total_payments()
        total_deposits += partner.deposits
        total_withdrawals += partner.withdrawals
        total_balance += partner.wallet_balance
    
    context = {
        'project': project,
        'partners': partners,
        'total_shares': total_shares,
        'shares_valid': shares_valid,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_balance': total_balance,
    }
    
    return render(request, 'partners/list.html', context)

def add_partner(request, project_id):
    """إضافة شريك للمشروع"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        partner_name = request.POST.get('partner_name')
        share_pct = Decimal(request.POST.get('share_pct', '0'))
        
        # البحث عن الشريك أو إنشاؤه
        partner, created = Partner.objects.get_or_create(
            name=partner_name,
            defaults={
                'phone': request.POST.get('phone', ''),
                'email': request.POST.get('email', ''),
            }
        )
        
        try:
            project_partner = ProjectPartner.objects.create(
                project=project,
                partner=partner,
                share_pct=share_pct
            )
            messages.success(request, f'تم إضافة الشريك {partner_name} بنجاح')
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('partners:list', project_id=project.id)
    
    return render(request, 'partners/add.html', {'project': project})

def create_receipt(request, project_id):
    """إنشاء سند قبض"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        partner_id = request.POST.get('partner_id')
        amount = Decimal(request.POST.get('amount', '0'))
        date = request.POST.get('date', datetime.now().date())
        description = request.POST.get('description', '')
        notes = request.POST.get('notes', '')
        
        project_partner = get_object_or_404(
            ProjectPartner, 
            project=project, 
            partner_id=partner_id
        )
        
        voucher = Voucher.objects.create(
            project=project,
            type='receipt',
            partner=project_partner.partner,
            project_partner=project_partner,
            amount=amount,
            date=date,
            description=description,
            notes=notes
        )
        
        # Handle attachment
        if request.FILES.get('attachment'):
            voucher.attachment = request.FILES['attachment']
            voucher.save()
        
        messages.success(request, f'تم إنشاء سند القبض رقم {voucher.ref_no}')
        return redirect('partners:list', project_id=project.id)
    
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    context = {
        'project': project,
        'partners': partners,
        'today': datetime.now().date()
    }
    return render(request, 'partners/create_receipt.html', context)

def create_payment(request, project_id):
    """إنشاء سند صرف"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        partner_id = request.POST.get('partner_id')
        amount = Decimal(request.POST.get('amount', '0'))
        date = request.POST.get('date', datetime.now().date())
        description = request.POST.get('description', '')
        notes = request.POST.get('notes', '')
        
        project_partner = get_object_or_404(
            ProjectPartner, 
            project=project, 
            partner_id=partner_id
        )
        
        try:
            voucher = Voucher.objects.create(
                project=project,
                type='payment',
                partner=project_partner.partner,
                project_partner=project_partner,
                amount=amount,
                date=date,
                description=description,
                notes=notes
            )
            
            # Handle attachment
            if request.FILES.get('attachment'):
                voucher.attachment = request.FILES['attachment']
                voucher.save()
            
            messages.success(request, f'تم إنشاء سند الصرف رقم {voucher.ref_no}')
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('partners:list', project_id=project.id)
    
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    context = {
        'project': project,
        'partners': partners,
        'today': datetime.now().date()
    }
    return render(request, 'partners/create_payment.html', context)

def wallets_summary(request, project_id):
    """ملخص محافظ الشركاء"""
    project = get_object_or_404(Project, id=project_id)
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    # حساب الإجماليات
    totals = {
        'balance': Decimal('0'),
        'deposits': Decimal('0'),
        'withdrawals': Decimal('0'),
        'available': Decimal('0'),
    }
    
    wallets = []
    for partner in partners:
        balance = partner.wallet_balance
        deposits = partner.get_total_receipts()
        withdrawals = partner.get_total_payments()
        credit_limit = partner.credit_limit
        available = balance + credit_limit
        
        # الأولوية
        priority_obj = WalletPriority.objects.filter(project_partner=partner).first()
        priority = priority_obj.priority if priority_obj else 3
        
        wallets.append({
            'partner': partner,
            'balance': balance,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'credit_limit': credit_limit,
            'available': available,
            'priority': priority,
        })
        
        totals['balance'] += balance
        totals['deposits'] += deposits
        totals['withdrawals'] += withdrawals
        totals['available'] += available
    
    # آخر المعاملات
    recent_transactions = Voucher.objects.filter(
        project=project
    ).select_related('partner').order_by('-date')[:10]
    
    context = {
        'project': project,
        'wallets': wallets,
        'totals': totals,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'partners/wallets.html', context)

def wallet_statement(request, project_id, partner_id):
    """كشف حساب محفظة شريك"""
    project = get_object_or_404(Project, id=project_id)
    partner = get_object_or_404(Partner, id=partner_id)
    project_partner = get_object_or_404(ProjectPartner, project=project, partner=partner)
    
    # المعاملات
    transactions = Voucher.objects.filter(
        project=project,
        partner=partner
    ).order_by('-date')
    
    context = {
        'project': project,
        'partner': partner,
        'project_partner': project_partner,
        'transactions': transactions,
    }
    
    return render(request, 'partners/wallet_statement.html', context)

def partners_statement(request, project_id):
    """كشف حساب الشركاء"""
    project = get_object_or_404(Project, id=project_id)
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    statements = []
    for partner in partners:
        vouchers = Voucher.objects.filter(
            project_partner=partner
        ).order_by('date', 'created_at')
        
        balance = Decimal('0.00')
        transactions = []
        
        for voucher in vouchers:
            if voucher.type == 'receipt':
                balance += voucher.amount
                trans_type = 'إيداع'
            else:
                balance -= voucher.amount
                trans_type = 'سحب'
            
            transactions.append({
                'date': voucher.date,
                'ref_no': voucher.ref_no,
                'type': trans_type,
                'amount': voucher.amount,
                'balance': balance,
                'description': voucher.description
            })
        
        statements.append({
            'partner': partner,
            'transactions': transactions,
            'final_balance': balance
        })
    
    context = {
        'project': project,
        'statements': statements,
    }
    
    return render(request, 'partners/statement.html', context)