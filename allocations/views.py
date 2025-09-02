from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from decimal import Decimal
from datetime import datetime

from .models import Allocation
from projects.models import Project, Stage
from partners.models import ProjectPartner

def allocate_delta(request, project_id, stage_id):
    """توزيع Delta للمرحلة"""
    project = get_object_or_404(Project, id=project_id)
    stage = get_object_or_404(Stage, id=stage_id, project=project)
    
    # حساب Delta
    delta = stage.get_delta()
    
    if request.method == 'POST':
        if delta <= 0:
            messages.error(request, 'لا يوجد فرق (Delta) للتوزيع')
            return redirect('projects:stage_detail', project_id=project.id, stage_id=stage.id)
        
        rule = request.POST.get('rule', 'by_share')
        
        # إنشاء التوزيع
        allocation = Allocation.objects.create(
            project=project,
            stage=stage,
            rule=rule,
            total_amount=delta,
            alloc_date=datetime.now().date()
        )
        
        if rule == 'by_share':
            # توزيع حسب الحصص
            allocation.prepare_allocation()
        else:
            # توزيع مخصص - يجب إدخال التفاصيل
            partners = ProjectPartner.objects.filter(project=project)
            details = {}
            
            for partner in partners:
                amount_key = f'amount_{partner.partner.id}'
                amount = Decimal(request.POST.get(amount_key, '0'))
                
                if amount > 0:
                    details[str(partner.partner.id)] = {
                        'partner_id': partner.partner.id,
                        'partner_name': partner.partner.name,
                        'share_pct': float(partner.share_pct),
                        'amount': float(amount)
                    }
            
            allocation.details_json = details
        
        try:
            # التحقق من صحة التوزيع
            allocation.validate_allocation()
            
            # ترحيل التوزيع
            if request.POST.get('post_now') == 'on':
                allocation.post()
                messages.success(request, f'تم توزيع {delta} على الشركاء بنجاح')
            else:
                allocation.save()
                messages.success(request, 'تم حفظ التوزيع كمسودة')
        
        except Exception as e:
            allocation.delete()
            messages.error(request, str(e))
            return redirect('projects:stage_detail', project_id=project.id, stage_id=stage.id)
        
        return redirect('allocations:history', project_id=project.id)
    
    # تحضير البيانات للعرض
    partners = ProjectPartner.objects.filter(project=project)
    
    # حساب التوزيع المقترح
    suggested_allocation = []
    for partner in partners:
        amount = delta * (partner.share_pct / Decimal('100'))
        amount = amount.quantize(Decimal('0.01'))
        suggested_allocation.append({
            'partner': partner,
            'amount': amount,
            'can_pay': partner.wallet_balance >= amount
        })
    
    context = {
        'project': project,
        'stage': stage,
        'delta': delta,
        'partners': partners,
        'suggested_allocation': suggested_allocation,
    }
    
    return render(request, 'allocations/allocate.html', context)

def allocations_history(request, project_id):
    """تاريخ التوزيعات"""
    project = get_object_or_404(Project, id=project_id)
    
    allocations = Allocation.objects.filter(
        project=project
    ).select_related('stage').order_by('-alloc_date', '-created_at')
    
    # فلترة
    stage_id = request.GET.get('stage')
    if stage_id:
        allocations = allocations.filter(stage_id=stage_id)
    
    posted = request.GET.get('posted')
    if posted == 'true':
        allocations = allocations.filter(posted=True)
    elif posted == 'false':
        allocations = allocations.filter(posted=False)
    
    # المجاميع
    totals = allocations.aggregate(
        count=Count('id'),
        total=Sum('total_amount'),
        posted_total=Sum('total_amount', filter=Q(posted=True))
    )
    
    stages = Stage.objects.filter(project=project)
    
    context = {
        'project': project,
        'allocations': allocations,
        'stages': stages,
        'totals': totals,
        'filters': {
            'stage': stage_id,
            'posted': posted,
        }
    }
    
    return render(request, 'allocations/history.html', context)