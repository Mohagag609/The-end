from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg, F
from decimal import Decimal
from datetime import datetime, timedelta
import json

from projects.models import Project, Stage
from partners.models import ProjectPartner, Voucher
from expenses.models import Expense
from purchases.models import PurchaseInvoice
from inventory.models import StockMove

def home(request):
    """الصفحة الرئيسية"""
    projects = Project.objects.all()
    
    # حساب الإحصائيات
    for project in projects:
        project.total_cost = Expense.objects.filter(project=project).aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        project.partners_count = ProjectPartner.objects.filter(project=project).count()
        project.stages_count = Stage.objects.filter(project=project).count()
        
    context = {
        'projects': projects,
    }
    
    return render(request, 'dashboard/home.html', context)

def project_dashboard(request, project_id):
    """لوحة تحكم المشروع"""
    project = get_object_or_404(Project, id=project_id)
    
    # الإحصائيات الأساسية
    stats = {
        'total_expenses': Expense.objects.filter(project=project).aggregate(
            total=Sum('amount'))['total'] or Decimal('0'),
        'total_deposits': Voucher.objects.filter(
            project=project, type='receipt'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'total_withdrawals': Voucher.objects.filter(
            project=project, type='payment'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'partners_count': ProjectPartner.objects.filter(project=project).count(),
        'stages_count': Stage.objects.filter(project=project).count(),
        'invoices_count': PurchaseInvoice.objects.filter(project=project).count(),
    }
    
    stats['net_balance'] = stats['total_deposits'] - stats['total_withdrawals']
    
    # آخر المعاملات
    recent_expenses = Expense.objects.filter(project=project).order_by('-date')[:5]
    recent_vouchers = Voucher.objects.filter(project=project).order_by('-date')[:5]
    
    # الشركاء
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    for partner in partners:
        partner.balance = partner.wallet_balance
    
    # المراحل
    stages = Stage.objects.filter(project=project)
    for stage in stages:
        stage.cost = stage.get_total_cost()
        stage.progress = min(100, (stage.cost / stage.budget * 100) if stage.budget > 0 else 0)
    
    context = {
        'project': project,
        'stats': stats,
        'recent_expenses': recent_expenses,
        'recent_vouchers': recent_vouchers,
        'partners': partners,
        'stages': stages,
    }
    
    return render(request, 'dashboard/project_dashboard_new.html', context)

def kpis(request, project_id):
    """صفحة مؤشرات الأداء"""
    project = get_object_or_404(Project, id=project_id)
    
    # حساب KPIs
    total_budget = Stage.objects.filter(project=project).aggregate(
        total=Sum('budget'))['total'] or Decimal('1')
    total_cost = Expense.objects.filter(project=project).aggregate(
        total=Sum('amount'))['total'] or Decimal('0')
    total_deposits = Voucher.objects.filter(
        project=project, type='receipt'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_withdrawals = Voucher.objects.filter(
        project=project, type='payment'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # حساب المؤشرات
    kpis = {
        'roi': float(((total_deposits - total_cost) / total_deposits * 100) if total_deposits > 0 else 0),
        'roi_trend': 5.2,  # مثال
        'cpi': float(total_budget / total_cost if total_cost > 0 else 1),
        'cpi_pct': min(100, float(total_budget / total_cost * 100 if total_cost > 0 else 100)),
        'burn_rate': float(total_cost / 3),  # assuming 3 months
        'months_remaining': float((total_deposits - total_withdrawals) / (total_cost / 3)) if total_cost > 0 else 12,
        'cash_flow': float(total_deposits - total_withdrawals),
        'liquidity_ratio': float((total_deposits - total_withdrawals) / total_cost if total_cost > 0 else 1),
        'completion_rate': 65.0,  # مثال
        'cost_efficiency': 87.5,  # مثال
        'budget_utilization': float(total_cost / total_budget * 100 if total_budget > 0 else 0),
        'avg_payment_delay': 5,  # مثال
    }
    
    # بيانات الرسوم البيانية
    
    # توزيع التكاليف
    cost_breakdown = [
        float(Expense.objects.filter(project=project, category='materials').aggregate(
            total=Sum('amount'))['total'] or 0),
        float(Expense.objects.filter(project=project, category='labor').aggregate(
            total=Sum('amount'))['total'] or 0),
        float(Expense.objects.filter(project=project, category='contractors').aggregate(
            total=Sum('amount'))['total'] or 0),
        float(Expense.objects.filter(project=project, category='admin').aggregate(
            total=Sum('amount'))['total'] or 0),
        float(Expense.objects.filter(project=project, category='other').aggregate(
            total=Sum('amount'))['total'] or 0),
    ]
    
    # الاتجاه الشهري
    monthly_labels = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو']
    monthly_expenses = [45000, 52000, 48000, 61000, 58000, 65000]
    monthly_deposits = [100000, 0, 50000, 0, 75000, 0]
    
    # تقدم المراحل
    stages = Stage.objects.filter(project=project)
    stage_names = [stage.name for stage in stages]
    stage_progress = []
    for stage in stages:
        cost = float(stage.get_total_cost())
        budget = float(stage.budget) if stage.budget > 0 else 1
        progress = min(100, (cost / budget * 100))
        stage_progress.append(progress)
    
    # مساهمات الشركاء
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    partner_names = [p.partner.name for p in partners]
    partner_contributions = []
    for partner in partners:
        deposits = float(partner.get_total_receipts())
        partner_contributions.append(deposits)
    
    # الميزانية مقابل الفعلي
    budget_actual_data = [
        float(total_budget),
        float(total_cost),
        float(total_budget - total_cost)
    ]
    
    context = {
        'project': project,
        'kpis': kpis,
        'cost_breakdown': json.dumps(cost_breakdown),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_expenses': json.dumps(monthly_expenses),
        'monthly_deposits': json.dumps(monthly_deposits),
        'stage_names': json.dumps(stage_names),
        'stage_progress': json.dumps(stage_progress),
        'partner_names': json.dumps(partner_names),
        'partner_contributions': json.dumps(partner_contributions),
        'budget_actual_data': json.dumps(budget_actual_data),
    }
    
    return render(request, 'dashboard/kpis.html', context)