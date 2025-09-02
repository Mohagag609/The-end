from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q, F
from decimal import Decimal
from datetime import datetime

from projects.models import Project, Warehouse
from .models import Item, ItemCategory, StockMove
from expenses.models import Expense
from partners.models import Voucher

def items_list(request, project_id):
    """قائمة الأصناف"""
    project = get_object_or_404(Project, id=project_id)
    
    # جلب جميع الأصناف
    items = Item.objects.all().select_related('category')
    
    # حساب الكميات المتاحة لكل صنف
    for item in items:
        # الكمية الواردة
        qty_in = StockMove.objects.filter(
            project=project,
            item=item,
            qty_in__gt=0
        ).aggregate(total=Sum('qty_in'))['total'] or Decimal('0')
        
        # الكمية الصادرة
        qty_out = StockMove.objects.filter(
            project=project,
            item=item,
            qty_out__gt=0
        ).aggregate(total=Sum('qty_out'))['total'] or Decimal('0')
        
        # الكمية المتاحة
        item.available_qty = qty_in - qty_out
        
        # القيمة الإجمالية
        item.total_value = item.available_qty * item.std_cost
        
        # حالة المخزون
        if item.available_qty <= 0:
            item.stock_status = 'out_of_stock'
            item.stock_status_label = 'نفذ'
            item.stock_status_color = 'red'
        elif item.available_qty < Decimal('10'):
            item.stock_status = 'low'
            item.stock_status_label = 'منخفض'
            item.stock_status_color = 'yellow'
        else:
            item.stock_status = 'available'
            item.stock_status_label = 'متوفر'
            item.stock_status_color = 'green'
    
    # الفئات للفلترة
    categories = ItemCategory.objects.all()
    
    context = {
        'project': project,
        'items': items,
        'categories': categories,
        'total_items': items.count(),
        'total_value': sum(item.total_value for item in items),
    }
    
    return render(request, 'inventory/items_list.html', context)

def add_item(request, project_id):
    """إضافة صنف جديد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            # إنشاء فئة جديدة إذا لزم
            category_id = request.POST.get('category_id')
            if category_id == 'new':
                category = ItemCategory.objects.create(
                    name=request.POST.get('new_category_name')
                )
            else:
                category = get_object_or_404(ItemCategory, id=category_id)
            
            # إنشاء الصنف
            item = Item.objects.create(
                name=request.POST.get('name'),
                sku=request.POST.get('sku'),
                category=category,
                uom=request.POST.get('uom'),
                std_cost=Decimal(request.POST.get('std_cost', '0'))
            )
            
            messages.success(request, f'تم إضافة الصنف "{item.name}" بنجاح')
            return redirect('inventory:items', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إضافة الصنف: {str(e)}')
    
    categories = ItemCategory.objects.all()
    
    context = {
        'project': project,
        'categories': categories,
        'units': [
            ('piece', 'قطعة'),
            ('kg', 'كيلوجرام'),
            ('ton', 'طن'),
            ('m', 'متر'),
            ('m2', 'متر مربع'),
            ('m3', 'متر مكعب'),
            ('liter', 'لتر'),
            ('box', 'كرتونة'),
        ]
    }
    
    return render(request, 'inventory/add_item.html', context)

def item_detail(request, project_id, item_id):
    """تفاصيل الصنف"""
    project = get_object_or_404(Project, id=project_id)
    item = get_object_or_404(Item, id=item_id)
    
    # حركات الصنف
    movements = StockMove.objects.filter(
        project=project,
        item=item
    ).order_by('-move_date', '-created_at')
    
    # إحصائيات
    stats = {
        'total_in': movements.filter(qty_in__gt=0).aggregate(Sum('qty_in'))['qty_in__sum'] or Decimal('0'),
        'total_out': movements.filter(qty_out__gt=0).aggregate(Sum('qty_out'))['qty_out__sum'] or Decimal('0'),
        'total_value_in': movements.filter(qty_in__gt=0).aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'total_value_out': movements.filter(qty_out__gt=0).aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
    }
    stats['balance'] = stats['total_in'] - stats['total_out']
    stats['balance_value'] = stats['balance'] * item.std_cost
    
    context = {
        'project': project,
        'item': item,
        'movements': movements,
        'stats': stats,
    }
    
    return render(request, 'inventory/item_detail.html', context)

def stock_movements(request, project_id):
    """حركات المخزون"""
    project = get_object_or_404(Project, id=project_id)
    
    movements = StockMove.objects.filter(
        project=project
    ).select_related('item', 'warehouse', 'stage').order_by('-move_date', '-created_at')
    
    # فلترة حسب النوع
    move_type = request.GET.get('type')
    if move_type == 'in':
        movements = movements.filter(qty_in__gt=0)
    elif move_type == 'out':
        movements = movements.filter(qty_out__gt=0)
    
    # فلترة حسب المخزن
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        movements = movements.filter(warehouse_id=warehouse_id)
    
    # المخازن للفلترة
    warehouses = Warehouse.objects.filter(project=project)
    
    context = {
        'project': project,
        'movements': movements,
        'warehouses': warehouses,
        'selected_type': move_type,
        'selected_warehouse': warehouse_id,
    }
    
    return render(request, 'inventory/movements.html', context)

def issue_stock(request, project_id):
    """صرف مواد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            item = get_object_or_404(Item, id=request.POST.get('item_id'))
            warehouse = get_object_or_404(Warehouse, id=request.POST.get('warehouse_id'))
            qty = Decimal(request.POST.get('qty'))
            
            # التحقق من الكمية المتاحة
            available = StockMove.get_available_qty(project, warehouse, item)
            if available < qty:
                messages.error(request, f'الكمية المتاحة ({available}) غير كافية')
                return redirect('inventory:issue', project_id=project.id)
            
            # إنشاء حركة الصرف
            move = StockMove.objects.create(
                project=project,
                warehouse=warehouse,
                item=item,
                ref_type='ISSUE',
                qty_out=qty,
                unit_cost=item.std_cost,
                move_date=request.POST.get('date', datetime.now().date()),
                notes=request.POST.get('notes', '')
            )
            
            # إنشاء مصروف إذا كان مرتبط بمرحلة
            stage_id = request.POST.get('stage_id')
            if stage_id:
                from projects.models import Stage
                stage = get_object_or_404(Stage, id=stage_id)
                move.stage = stage
                move.save()
                
                # إنشاء مصروف تلقائي
                expense = Expense.objects.create(
                    project=project,
                    stage=stage,
                    category='materials',
                    description=f'صرف {item.name} - {qty} {item.uom}',
                    amount=move.amount,
                    date=move.move_date,
                    payee_type='internal',
                    payee_name='المخزن',
                    ref_type='STOCK_ISSUE',
                    ref_id=move.id
                )
                
                messages.success(request, f'تم صرف {qty} {item.uom} من {item.name}')
            else:
                messages.success(request, f'تم صرف {qty} {item.uom} من {item.name}')
            
            return redirect('inventory:movements', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في صرف المواد: {str(e)}')
    
    # البيانات للفورم
    items = Item.objects.all()
    warehouses = Warehouse.objects.filter(project=project)
    from projects.models import Stage
    stages = Stage.objects.filter(project=project, status='active')
    
    # حساب الكميات المتاحة
    for item in items:
        item.available_qty = Decimal('0')
        for warehouse in warehouses:
            item.available_qty += StockMove.get_available_qty(project, warehouse, item)
    
    context = {
        'project': project,
        'items': items,
        'warehouses': warehouses,
        'stages': stages,
    }
    
    return render(request, 'inventory/issue_stock.html', context)

def receive_stock(request, project_id):
    """استلام مواد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        try:
            item = get_object_or_404(Item, id=request.POST.get('item_id'))
            warehouse = get_object_or_404(Warehouse, id=request.POST.get('warehouse_id'))
            
            move = StockMove.objects.create(
                project=project,
                warehouse=warehouse,
                item=item,
                ref_type='RECEIVE',
                qty_in=Decimal(request.POST.get('qty')),
                unit_cost=Decimal(request.POST.get('unit_cost', item.std_cost)),
                move_date=request.POST.get('date', datetime.now().date()),
                notes=request.POST.get('notes', '')
            )
            
            messages.success(request, f'تم استلام {move.qty_in} {item.uom} من {item.name}')
            return redirect('inventory:movements', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في استلام المواد: {str(e)}')
    
    items = Item.objects.all()
    warehouses = Warehouse.objects.filter(project=project)
    
    context = {
        'project': project,
        'items': items,
        'warehouses': warehouses,
    }
    
    return render(request, 'inventory/receive_stock.html', context)

def warehouses_list(request, project_id):
    """قائمة المخازن"""
    project = get_object_or_404(Project, id=project_id)
    warehouses = Warehouse.objects.filter(project=project)
    
    # حساب إحصائيات كل مخزن
    for warehouse in warehouses:
        # عدد الأصناف
        warehouse.items_count = StockMove.objects.filter(
            project=project,
            warehouse=warehouse
        ).values('item').distinct().count()
        
        # القيمة الإجمالية
        movements = StockMove.objects.filter(
            project=project,
            warehouse=warehouse
        )
        
        total_in = movements.filter(qty_in__gt=0).aggregate(
            total=Sum(F('qty_in') * F('unit_cost'))
        )['total'] or Decimal('0')
        
        total_out = movements.filter(qty_out__gt=0).aggregate(
            total=Sum(F('qty_out') * F('unit_cost'))
        )['total'] or Decimal('0')
        
        warehouse.total_value = total_in - total_out
    
    context = {
        'project': project,
        'warehouses': warehouses,
    }
    
    return render(request, 'inventory/warehouses.html', context)

def warehouse_detail(request, project_id, warehouse_id):
    """تفاصيل المخزن"""
    project = get_object_or_404(Project, id=project_id)
    warehouse = get_object_or_404(Warehouse, id=warehouse_id, project=project)
    
    # الأصناف في المخزن
    items_data = []
    items = Item.objects.all()
    
    for item in items:
        qty = StockMove.get_available_qty(project, warehouse, item)
        if qty > 0:
            items_data.append({
                'item': item,
                'qty': qty,
                'value': qty * item.std_cost
            })
    
    # آخر الحركات
    recent_movements = StockMove.objects.filter(
        project=project,
        warehouse=warehouse
    ).select_related('item').order_by('-move_date', '-created_at')[:10]
    
    context = {
        'project': project,
        'warehouse': warehouse,
        'items_data': items_data,
        'recent_movements': recent_movements,
        'total_value': sum(item['value'] for item in items_data),
    }
    
    return render(request, 'inventory/warehouse_detail.html', context)