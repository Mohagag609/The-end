from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime

from .models import PartnerSettleBatch, PartnerSettleLine, PartnerClaim
from projects.models import Project
from partners.models import ProjectPartner

def settlements_list(request, project_id):
    """قائمة التسويات"""
    project = get_object_or_404(Project, id=project_id)
    
    batches = PartnerSettleBatch.objects.filter(
        project=project
    ).order_by('-cutoff_date', '-created_at')
    
    context = {
        'project': project,
        'batches': batches,
    }
    
    return render(request, 'settlements/list.html', context)

def create_settlement(request, project_id):
    """إنشاء تسوية جديدة"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        cutoff_date = request.POST.get('cutoff_date')
        notes = request.POST.get('notes', '')
        
        # التحقق من عدم وجود تسوية مفتوحة
        if PartnerSettleBatch.objects.filter(
            project=project,
            status='open'
        ).exists():
            messages.error(request, 'يوجد تسوية مفتوحة بالفعل. يجب ترحيلها أو حذفها أولاً')
            return redirect('settlements:list', project_id=project.id)
        
        # إنشاء دفعة التسوية
        batch = PartnerSettleBatch.objects.create(
            project=project,
            cutoff_date=cutoff_date,
            notes=notes,
            status='open'
        )
        
        # تحضير التسوية
        batch.prepare_settlement()
        
        # توليد المطالبات
        batch.generate_claims()
        
        messages.success(request, 'تم إنشاء التسوية بنجاح')
        return redirect('settlements:detail', project_id=project.id, batch_id=batch.id)
    
    # الحصول على آخر تاريخ تسوية
    last_batch = PartnerSettleBatch.objects.filter(
        project=project,
        status='posted'
    ).order_by('-cutoff_date').first()
    
    context = {
        'project': project,
        'last_batch': last_batch,
        'suggested_date': datetime.now().date(),
    }
    
    return render(request, 'settlements/create.html', context)

def settlement_detail(request, project_id, batch_id):
    """تفاصيل التسوية"""
    project = get_object_or_404(Project, id=project_id)
    batch = get_object_or_404(PartnerSettleBatch, id=batch_id, project=project)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'post' and batch.status == 'open':
            try:
                batch.post()
                messages.success(request, 'تم ترحيل التسوية بنجاح')
            except Exception as e:
                messages.error(request, str(e))
        
        elif action == 'reverse' and batch.status == 'posted':
            try:
                batch.reverse()
                messages.success(request, 'تم عكس التسوية')
            except Exception as e:
                messages.error(request, str(e))
        
        elif action == 'regenerate_claims' and batch.status == 'open':
            batch.generate_claims()
            messages.success(request, 'تم إعادة توليد المطالبات')
        
        return redirect('settlements:detail', project_id=project.id, batch_id=batch.id)
    
    # سطور التسوية
    lines = batch.lines.all().select_related('partner', 'project_partner')
    
    # تقسيم الشركاء
    creditors = []  # الدائنون
    debtors = []   # المدينون
    balanced = []   # المتوازنون
    
    for line in lines:
        if line.diff > 0:
            creditors.append(line)
        elif line.diff < 0:
            debtors.append(line)
        else:
            balanced.append(line)
    
    # المطالبات
    claims = batch.claims.all().select_related('from_partner', 'to_partner')
    
    context = {
        'project': project,
        'batch': batch,
        'lines': lines,
        'creditors': creditors,
        'debtors': debtors,
        'balanced': balanced,
        'claims': claims,
    }
    
    return render(request, 'settlements/detail.html', context)