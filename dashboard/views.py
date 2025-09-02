from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from projects.models import Project, Stage
from partners.models import Partner, ProjectPartner, Voucher
from suppliers.models import Supplier
from purchases.models import PurchaseInvoice
from expenses.models import Expense
from inventory.models import StockMove

def home(request):
    """الصفحة الرئيسية - قائمة المشروعات"""
    projects = Project.objects.all().order_by('-created_at')
    
    # إحصائيات لكل مشروع
    for project in projects:
        project.stages_count = project.stages.count()
        project.partners_count = project.projectpartner_set.count()
        project.total_cost = project.get_total_cost()
        
        # حساب إجمالي المحافظ
        project.total_wallets = ProjectPartner.objects.filter(
            project=project
        ).aggregate(
            total=Sum('wallet_balance')
        )['total'] or Decimal('0.00')
    
    context = {
        'projects': projects,
        'projects_count': projects.count(),
        'active_projects': projects.filter(status='open').count(),
    }
    
    return render(request, 'dashboard/home.html', context)

def project_dashboard(request, project_id):
    """لوحة تحكم المشروع"""
    project = Project.objects.get(id=project_id)
    
    # إحصائيات المشروع
    stats = {
        'total_purchases': PurchaseInvoice.objects.filter(
            project=project, 
            status='posted'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00'),
        
        'total_expenses': Expense.objects.filter(
            project=project
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        
        'total_stock_issues': StockMove.objects.filter(
            project=project,
            qty_out__gt=0
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        
        'partners_deposits': Voucher.objects.filter(
            project=project,
            type='receipt'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        
        'partners_withdrawals': Voucher.objects.filter(
            project=project,
            type='payment'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
    }
    
    stats['total_cost'] = stats['total_expenses'] + stats['total_stock_issues']
    stats['wallet_balance'] = stats['partners_deposits'] - stats['partners_withdrawals']
    stats['treasury_balance'] = stats['partners_deposits'] - stats['total_cost']
    
    # الشركاء
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    for partner in partners:
        partner.deposits = partner.get_total_receipts()
        partner.withdrawals = partner.get_total_payments()
        partner.net_balance = partner.wallet_balance
    
    # المراحل
    stages = Stage.objects.filter(project=project).order_by('created_at')
    for stage in stages:
        stage.total_cost = stage.get_total_cost()
        stage.delta = stage.get_delta()
        stage.is_over = stage.is_over_budget()
    
    # آخر المعاملات
    recent_vouchers = Voucher.objects.filter(
        project=project
    ).order_by('-date', '-created_at')[:10]
    
    recent_expenses = Expense.objects.filter(
        project=project
    ).order_by('-date', '-created_at')[:10]
    
    recent_purchases = PurchaseInvoice.objects.filter(
        project=project
    ).order_by('-date', '-created_at')[:5]
    
    context = {
        'project': project,
        'stats': stats,
        'partners': partners,
        'stages': stages,
        'recent_vouchers': recent_vouchers,
        'recent_expenses': recent_expenses,
        'recent_purchases': recent_purchases,
    }
    
    return render(request, 'dashboard/project_dashboard.html', context)

def kpis_dashboard(request):
    """شاشة المؤشرات الرئيسية KPIs"""
    # يمكن فلترة حسب المشروع
    project_id = request.GET.get('project')
    
    if project_id:
        project = Project.objects.get(id=project_id)
        purchases_qs = PurchaseInvoice.objects.filter(project=project, status='posted')
        expenses_qs = Expense.objects.filter(project=project)
        vouchers_qs = Voucher.objects.filter(project=project)
        stock_qs = StockMove.objects.filter(project=project)
    else:
        project = None
        purchases_qs = PurchaseInvoice.objects.filter(status='posted')
        expenses_qs = Expense.objects.all()
        vouchers_qs = Voucher.objects.all()
        stock_qs = StockMove.objects.all()
    
    # حساب المؤشرات
    kpis = {
        # المشتريات
        'total_purchases': purchases_qs.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0.00'),
        
        'purchases_count': purchases_qs.count(),
        
        # المصروفات
        'total_expenses': expenses_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00'),
        
        'expenses_count': expenses_qs.count(),
        
        # صرف المواد
        'total_stock_issues': stock_qs.filter(
            qty_out__gt=0
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00'),
        
        # محافظ الشركاء
        'total_deposits': vouchers_qs.filter(
            type='receipt'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00'),
        
        'total_withdrawals': vouchers_qs.filter(
            type='payment'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00'),
        
        # الموردون
        'suppliers_count': Supplier.objects.filter(is_active=True).count(),
        
        # المشروعات
        'projects_count': Project.objects.count(),
        'active_projects': Project.objects.filter(status='open').count(),
    }
    
    # حسابات إضافية
    kpis['total_cost'] = kpis['total_expenses'] + kpis['total_stock_issues']
    kpis['wallet_balance'] = kpis['total_deposits'] - kpis['total_withdrawals']
    kpis['treasury_balance'] = kpis['total_deposits'] - kpis['total_cost']
    
    # رسوم بيانية - بيانات للـ 30 يوم الماضية
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # مصروفات يومية
    daily_expenses = []
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        amount = expenses_qs.filter(date=date).aggregate(
            total=Sum('amount')
        )['total'] or 0
        daily_expenses.append({
            'date': date.strftime('%Y-%m-%d'),
            'amount': float(amount)
        })
    
    context = {
        'project': project,
        'projects': Project.objects.all(),
        'kpis': kpis,
        'daily_expenses': daily_expenses,
    }
    
    return render(request, 'dashboard/kpis.html', context)