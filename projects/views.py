from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from decimal import Decimal

from .models import Project, Stage, Warehouse
from partners.models import ProjectPartner
from core.models import Currency

def create_project(request):
    """إنشاء مشروع جديد"""
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        # التحقق من عدم تكرار الكود
        if Project.objects.filter(code=code).exists():
            messages.error(request, f'كود المشروع {code} موجود بالفعل')
            return redirect('dashboard:home')
        
        # الحصول على العملة الافتراضية
        currency = Currency.objects.filter(is_default=True).first()
        if not currency:
            # إنشاء عملة افتراضية إذا لم تكن موجودة
            currency = Currency.objects.create(
                code='EGP',
                name='جنيه مصري',
                symbol='ج.م',
                is_default=True
            )
        
        project = Project.objects.create(
            code=code,
            name=name,
            description=description,
            currency=currency
        )
        
        # إنشاء مخزن افتراضي
        Warehouse.objects.create(
            project=project,
            name='المخزن الرئيسي',
            location='الموقع الرئيسي'
        )
        
        messages.success(request, f'تم إنشاء المشروع {name} بنجاح')
        return redirect('dashboard:project_dashboard', project_id=project.id)
    
    return redirect('dashboard:home')

def project_detail(request, project_id):
    """تفاصيل المشروع"""
    project = get_object_or_404(Project, id=project_id)
    
    # الشركاء
    partners = ProjectPartner.objects.filter(project=project).select_related('partner')
    total_shares = partners.aggregate(total=Sum('share_pct'))['total'] or Decimal('0.00')
    
    # المراحل
    stages = Stage.objects.filter(project=project).order_by('created_at')
    
    # المخازن
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    
    context = {
        'project': project,
        'partners': partners,
        'total_shares': total_shares,
        'shares_valid': total_shares == Decimal('100.00'),
        'stages': stages,
        'warehouses': warehouses,
    }
    
    return render(request, 'projects/detail.html', context)

def stages_list(request, project_id):
    """قائمة المراحل"""
    project = get_object_or_404(Project, id=project_id)
    stages = Stage.objects.filter(project=project).order_by('created_at')
    
    # حساب الإحصائيات
    totals = {
        'budget': Decimal('0'),
        'cost': Decimal('0'),
        'variance': Decimal('0'),
        'completion': 0,
    }
    
    stages_data = []
    for stage in stages:
        actual_cost = stage.get_total_cost()
        allocated = stage.get_allocated_amount()
        delta = stage.get_delta()
        progress = min(100, (actual_cost / stage.budget * 100) if stage.budget > 0 else 0)
        
        stages_data.append({
            'id': stage.id,
            'name': stage.name,
            'description': stage.description,
            'budget': stage.budget or Decimal('0'),
            'actual_cost': actual_cost,
            'allocated': allocated,
            'delta': delta,
            'progress': progress,
            'start_date': stage.start_date,
            'end_date': stage.end_date,
        })
        
        totals['budget'] += stage.budget or Decimal('0')
        totals['cost'] += actual_cost
    
    totals['variance'] = totals['budget'] - totals['cost']
    totals['completion'] = (totals['cost'] / totals['budget'] * 100) if totals['budget'] > 0 else 0
    
    # آخر المصروفات
    from expenses.models import Expense
    recent_expenses = Expense.objects.filter(
        project=project,
        stage__isnull=False
    ).select_related('stage').order_by('-date')[:10]
    
    # المخازن
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    
    # الفئات
    from inventory.models import ItemCategory
    categories = ItemCategory.objects.all()
    
    context = {
        'project': project,
        'stages': stages_data,
        'totals': totals,
        'recent_expenses': recent_expenses,
        'warehouses': warehouses,
        'categories': categories,
    }
    
    return render(request, 'projects/stages.html', context)

def add_stage(request, project_id):
    """إضافة مرحلة جديدة"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        budget = Decimal(request.POST.get('budget', '0'))
        description = request.POST.get('description', '')
        
        stage = Stage.objects.create(
            project=project,
            name=name,
            budget=budget,
            description=description,
            status='pending'
        )
        
        messages.success(request, f'تم إضافة المرحلة "{name}" بنجاح')
        return redirect('projects:stages', project_id=project.id)
    
    return redirect('projects:stages', project_id=project.id)

def create_stage(request, project_id):
    """إنشاء مرحلة جديدة"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        budget = Decimal(request.POST.get('budget', '0'))
        
        stage = Stage.objects.create(
            project=project,
            name=name,
            description=description,
            budget=budget,
            status='pending'
        )
        
        messages.success(request, f'تم إنشاء المرحلة {name} بنجاح')
        
        if request.headers.get('HX-Request'):
            # HTMX request
            stages = Stage.objects.filter(project=project).order_by('created_at')
            for s in stages:
                s.total_cost = s.get_total_cost()
                s.delta = s.get_delta()
            return render(request, 'projects/partials/stages_list.html', {
                'project': project,
                'stages': stages
            })
        
        return redirect('projects:stages', project_id=project.id)
    
    return render(request, 'projects/create_stage.html', {
        'project': project
    })

def stage_detail(request, project_id, stage_id):
    """تفاصيل المرحلة"""
    project = get_object_or_404(Project, id=project_id)
    stage = get_object_or_404(Stage, id=stage_id, project=project)
    
    # حساب التكاليف
    from expenses.models import Expense
    from inventory.models import StockMove
    
    expenses = Expense.objects.filter(stage=stage).order_by('-date')
    stock_issues = StockMove.objects.filter(
        stage=stage,
        qty_out__gt=0
    ).order_by('-move_date')
    
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_stock = stock_issues.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    stage.total_cost = total_expenses + total_stock
    stage.allocated = stage.get_allocated_amount()
    stage.delta = stage.get_delta()
    
    # التوزيعات
    from allocations.models import Allocation
    allocations = Allocation.objects.filter(stage=stage).order_by('-alloc_date')
    
    context = {
        'project': project,
        'stage': stage,
        'expenses': expenses[:10],
        'stock_issues': stock_issues[:10],
        'allocations': allocations,
        'total_expenses': total_expenses,
        'total_stock': total_stock,
    }
    
    return render(request, 'projects/stage_detail.html', context)

def warehouses_list(request, project_id):
    """قائمة المخازن"""
    project = get_object_or_404(Project, id=project_id)
    warehouses = Warehouse.objects.filter(project=project).order_by('name')
    
    # حساب رصيد كل مخزن
    for warehouse in warehouses:
        from inventory.models import Item
        items_count = Item.objects.filter(
            stock_moves__warehouse=warehouse
        ).distinct().count()
        warehouse.items_count = items_count
    
    context = {
        'project': project,
        'warehouses': warehouses,
    }
    
    return render(request, 'projects/warehouses.html', context)

def create_warehouse(request, project_id):
    """إنشاء مخزن جديد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location', '')
        
        warehouse = Warehouse.objects.create(
            project=project,
            name=name,
            location=location
        )
        
        messages.success(request, f'تم إنشاء المخزن {name} بنجاح')
        return redirect('projects:warehouses', project_id=project.id)
    
    return render(request, 'projects/create_warehouse.html', {
        'project': project
    })