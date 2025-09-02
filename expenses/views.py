from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.http import JsonResponse
from decimal import Decimal
from datetime import datetime

from .models import Expense
from projects.models import Project, Stage

def expenses_list(request, project_id):
    """قائمة المصروفات"""
    project = get_object_or_404(Project, id=project_id)
    
    expenses = Expense.objects.filter(
        project=project
    ).select_related('stage').order_by('-date', '-created_at')
    
    # فلترة
    stage_id = request.GET.get('stage')
    if stage_id:
        expenses = expenses.filter(stage_id=stage_id)
    
    category = request.GET.get('category')
    if category:
        expenses = expenses.filter(category=category)
    
    payee_type = request.GET.get('payee_type')
    if payee_type:
        expenses = expenses.filter(payee_type=payee_type)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    
    # المجاميع
    totals = expenses.aggregate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    # مجاميع حسب الفئة
    by_category = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    stages = Stage.objects.filter(project=project)
    
    context = {
        'project': project,
        'expenses': expenses[:100],  # عرض أول 100 مصروف
        'stages': stages,
        'totals': totals,
        'by_category': by_category,
        'categories': Expense.EXPENSE_CATEGORIES,
        'payee_types': Expense.PAYEE_TYPES,
        'filters': {
            'stage': stage_id,
            'category': category,
            'payee_type': payee_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'expenses/list.html', context)

def create_expense(request, project_id):
    """إنشاء مصروف"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        stage_id = request.POST.get('stage_id')
        amount = Decimal(request.POST.get('amount', '0'))
        date = request.POST.get('date', datetime.now().date())
        category = request.POST.get('category', 'other')
        payee_type = request.POST.get('payee_type', 'other')
        payee_name = request.POST.get('payee_name', '')
        description = request.POST.get('description', '')
        reference = request.POST.get('reference', '')
        
        stage = get_object_or_404(Stage, id=stage_id, project=project) if stage_id else None
        
        expense = Expense.objects.create(
            project=project,
            stage=stage,
            amount=amount,
            date=date,
            category=category,
            payee_type=payee_type,
            payee_name=payee_name,
            description=description,
            reference=reference
        )
        
        # رفع المرفق إن وجد
        if request.FILES.get('attachment'):
            expense.attachment = request.FILES['attachment']
            expense.save()
        
        messages.success(request, f'تم إضافة المصروف بقيمة {amount} بنجاح')
        
        if stage:
            messages.info(request, f'تم إضافة المصروف للمرحلة {stage.name}')
        
        return redirect('expenses:list', project_id=project.id)
    
    stages = Stage.objects.filter(project=project, status__in=['pending', 'active'])
    
    context = {
        'project': project,
        'stages': stages,
        'categories': Expense.EXPENSE_CATEGORIES,
        'payee_types': Expense.PAYEE_TYPES,
    }
    
    return render(request, 'expenses/create.html', context)

def quick_expense(request, project_id):
    """مصروف سريع (HTMX)"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        stage_id = request.POST.get('stage_id')
        amount = Decimal(request.POST.get('amount', '0'))
        description = request.POST.get('description', '')
        
        if amount <= 0:
            return JsonResponse({'error': 'المبلغ غير صحيح'}, status=400)
        
        stage = get_object_or_404(Stage, id=stage_id, project=project) if stage_id else None
        
        expense = Expense.objects.create(
            project=project,
            stage=stage,
            amount=amount,
            date=datetime.now().date(),
            category='other',
            payee_type='other',
            description=description
        )
        
        # إرجاع HTML للمصروف الجديد
        return render(request, 'expenses/partials/expense_row.html', {
            'expense': expense
        })
    
    stages = Stage.objects.filter(project=project, status__in=['pending', 'active'])
    
    return render(request, 'expenses/partials/quick_form.html', {
        'project': project,
        'stages': stages
    })