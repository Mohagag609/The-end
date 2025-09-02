from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q, F
from django.db import transaction
from decimal import Decimal
from datetime import datetime

from projects.models import Project
from .models import Partner, ProjectPartner, Voucher, WalletPriority

def partners_list(request, project_id):
    """قائمة الشركاء"""
    project = get_object_or_404(Project, id=project_id)
    
    # جلب شركاء المشروع
    project_partners = ProjectPartner.objects.filter(
        project=project
    ).select_related('partner')
    
    # حساب الأرصدة
    for pp in project_partners:
        # الإيداعات
        deposits = Voucher.objects.filter(
            project=project,
            partner=pp.partner,
            type='receipt'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # المسحوبات
        withdrawals = Voucher.objects.filter(
            project=project,
            partner=pp.partner,
            type='payment'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # الرصيد
        pp.deposits = deposits
        pp.withdrawals = withdrawals
        pp.balance = deposits - withdrawals + pp.carry_forward_balance
        pp.available = pp.balance
        
        # حد الائتمان
        if pp.credit_limit > 0:
            pp.available = pp.balance + pp.credit_limit
    
    # إجمالي الحصص
    total_shares = project_partners.aggregate(total=Sum('share_pct'))['total'] or Decimal('0')
    shares_valid = total_shares == Decimal('100')
    
    context = {
        'project': project,
        'partners': project_partners,
        'total_shares': total_shares,
        'shares_valid': shares_valid,
        'total_deposits': sum(pp.deposits for pp in project_partners),
        'total_withdrawals': sum(pp.withdrawals for pp in project_partners),
        'total_balance': sum(pp.balance for pp in project_partners),
    }
    
    return render(request, 'partners/list_simple.html', context)

def add_partner(request, project_id):
    """إضافة شريك جديد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            # إنشاء الشريك
            partner = Partner.objects.create(
                name=request.POST.get('name'),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
                national_id=request.POST.get('national_id', '')
            )
            
            # ربط الشريك بالمشروع
            project_partner = ProjectPartner.objects.create(
                project=project,
                partner=partner,
                share_pct=Decimal(request.POST.get('share_pct', '0')),
                credit_limit=Decimal(request.POST.get('credit_limit', '0')),
                carry_forward_balance=Decimal(request.POST.get('carry_forward_balance', '0'))
            )
            
            messages.success(request, f'تم إضافة الشريك "{partner.name}" بنجاح')
            return redirect('partners:list', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إضافة الشريك: {str(e)}')
    
    # الشركاء الموجودين (لاختيار شريك موجود)
    existing_partners = Partner.objects.exclude(
        id__in=ProjectPartner.objects.filter(project=project).values_list('partner_id', flat=True)
    )
    
    context = {
        'project': project,
        'existing_partners': existing_partners,
    }
    
    return render(request, 'partners/add_partner.html', context)

def partner_detail(request, project_id, partner_id):
    """تفاصيل الشريك"""
    project = get_object_or_404(Project, id=project_id)
    partner = get_object_or_404(Partner, id=partner_id)
    project_partner = get_object_or_404(ProjectPartner, project=project, partner=partner)
    
    # السندات
    vouchers = Voucher.objects.filter(
        project=project,
        partner=partner
    ).order_by('-date', '-created_at')
    
    # الإحصائيات
    stats = {
        'total_deposits': vouchers.filter(type='receipt').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'total_withdrawals': vouchers.filter(type='payment').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
    }
    stats['balance'] = stats['total_deposits'] - stats['total_withdrawals'] + project_partner.carry_forward_balance
    stats['available'] = stats['balance'] + project_partner.credit_limit
    
    context = {
        'project': project,
        'partner': partner,
        'project_partner': project_partner,
        'vouchers': vouchers[:10],  # آخر 10 سندات
        'stats': stats,
    }
    
    return render(request, 'partners/partner_detail.html', context)

def wallets_summary(request, project_id):
    """ملخص المحافظ"""
    project = get_object_or_404(Project, id=project_id)
    
    # جلب شركاء المشروع
    project_partners = ProjectPartner.objects.filter(
        project=project
    ).select_related('partner')
    
    # حساب أرصدة المحافظ
    wallets_data = []
    for pp in project_partners:
        # الإيداعات
        deposits = Voucher.objects.filter(
            project=project,
            partner=pp.partner,
            type='receipt'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # المسحوبات
        withdrawals = Voucher.objects.filter(
            project=project,
            partner=pp.partner,
            type='payment'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # الرصيد
        balance = deposits - withdrawals + pp.carry_forward_balance
        available = balance + pp.credit_limit if pp.credit_limit > 0 else balance
        
        # آخر حركة
        last_voucher = Voucher.objects.filter(
            project=project,
            partner=pp.partner
        ).order_by('-date', '-created_at').first()
        
        wallets_data.append({
            'partner': pp.partner,
            'project_partner': pp,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'balance': balance,
            'available': available,
            'credit_limit': pp.credit_limit,
            'last_movement': last_voucher,
            'share_pct': pp.share_pct,
        })
    
    # الإجماليات
    totals = {
        'deposits': sum(w['deposits'] for w in wallets_data),
        'withdrawals': sum(w['withdrawals'] for w in wallets_data),
        'balance': sum(w['balance'] for w in wallets_data),
        'available': sum(w['available'] for w in wallets_data),
    }
    
    context = {
        'project': project,
        'wallets': wallets_data,
        'totals': totals,
    }
    
    return render(request, 'partners/wallets_summary.html', context)

def wallet_detail(request, project_id, partner_id):
    """كشف حساب المحفظة"""
    project = get_object_or_404(Project, id=project_id)
    partner = get_object_or_404(Partner, id=partner_id)
    project_partner = get_object_or_404(ProjectPartner, project=project, partner=partner)
    
    # السندات
    vouchers = Voucher.objects.filter(
        project=project,
        partner=partner
    ).order_by('date', 'created_at')
    
    # حساب الرصيد التراكمي
    running_balance = project_partner.carry_forward_balance
    for voucher in vouchers:
        if voucher.type == 'receipt':
            running_balance += voucher.amount
        else:
            running_balance -= voucher.amount
        voucher.running_balance = running_balance
    
    # الإحصائيات
    stats = {
        'total_deposits': vouchers.filter(type='receipt').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'total_withdrawals': vouchers.filter(type='payment').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'carry_forward': project_partner.carry_forward_balance,
    }
    stats['final_balance'] = stats['carry_forward'] + stats['total_deposits'] - stats['total_withdrawals']
    
    context = {
        'project': project,
        'partner': partner,
        'project_partner': project_partner,
        'vouchers': vouchers,
        'stats': stats,
    }
    
    return render(request, 'partners/wallet_detail.html', context)

def create_receipt(request, project_id):
    """إنشاء سند قبض"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            partner = get_object_or_404(Partner, id=request.POST.get('partner_id'))
            project_partner = get_object_or_404(ProjectPartner, project=project, partner=partner)
            
            voucher = Voucher.objects.create(
                project=project,
                partner=partner,
                project_partner=project_partner,
                type='receipt',
                amount=Decimal(request.POST.get('amount')),
                date=request.POST.get('date', datetime.now().date()),
                description=request.POST.get('description', ''),
                notes=request.POST.get('notes', '')
            )
            
            messages.success(request, f'تم إنشاء سند القبض رقم {voucher.ref_no} بنجاح')
            return redirect('partners:wallets', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء سند القبض: {str(e)}')
    
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    context = {
        'project': project,
        'partners': partners,
        'voucher_type': 'receipt',
    }
    
    return render(request, 'partners/create_voucher.html', context)

def create_payment(request, project_id):
    """إنشاء سند صرف"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            partner = get_object_or_404(Partner, id=request.POST.get('partner_id'))
            project_partner = get_object_or_404(ProjectPartner, project=project, partner=partner)
            amount = Decimal(request.POST.get('amount'))
            
            # التحقق من الرصيد
            if not project_partner.can_withdraw(amount):
                messages.error(request, 'الرصيد غير كافي للصرف')
                return redirect('partners:create_payment', project_id=project.id)
            
            voucher = Voucher.objects.create(
                project=project,
                partner=partner,
                project_partner=project_partner,
                type='payment',
                amount=amount,
                date=request.POST.get('date', datetime.now().date()),
                description=request.POST.get('description', ''),
                notes=request.POST.get('notes', '')
            )
            
            messages.success(request, f'تم إنشاء سند الصرف رقم {voucher.ref_no} بنجاح')
            return redirect('partners:wallets', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء سند الصرف: {str(e)}')
    
    # الشركاء مع أرصدتهم
    partners_data = []
    project_partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    
    for pp in project_partners:
        balance = pp.get_balance()
        available = balance + pp.credit_limit if pp.credit_limit > 0 else balance
        
        partners_data.append({
            'partner': pp.partner,
            'balance': balance,
            'available': available,
            'can_withdraw': available > 0
        })
    
    context = {
        'project': project,
        'partners': partners_data,
        'voucher_type': 'payment',
    }
    
    return render(request, 'partners/create_voucher.html', context)

def vouchers_list(request, project_id):
    """قائمة السندات"""
    project = get_object_or_404(Project, id=project_id)
    
    vouchers = Voucher.objects.filter(
        project=project
    ).select_related('partner').order_by('-date', '-created_at')
    
    # فلترة حسب النوع
    voucher_type = request.GET.get('type')
    if voucher_type in ['receipt', 'payment']:
        vouchers = vouchers.filter(type=voucher_type)
    
    # فلترة حسب الشريك
    partner_id = request.GET.get('partner')
    if partner_id:
        vouchers = vouchers.filter(partner_id=partner_id)
    
    # الشركاء للفلترة
    partners = Partner.objects.filter(
        id__in=ProjectPartner.objects.filter(project=project).values_list('partner_id', flat=True)
    )
    
    context = {
        'project': project,
        'vouchers': vouchers,
        'partners': partners,
        'selected_type': voucher_type,
        'selected_partner': partner_id,
    }
    
    return render(request, 'partners/vouchers_list.html', context)