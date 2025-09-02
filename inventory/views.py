from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime

from .models import Item, ItemCategory, StockMove
from projects.models import Project, Stage, Warehouse

def inventory_list(request, project_id):
    """قائمة المخزون للمشروع"""
    project = get_object_or_404(Project, id=project_id)
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    
    # جمع الأصناف في كل المخازن
    items_data = []
    items = Item.objects.filter(
        stock_moves__project=project
    ).distinct()
    
    for item in items:
        item_info = {
            'item': item,
            'warehouses': []
        }
        
        total_qty = Decimal('0.000')
        for warehouse in warehouses:
            qty = item.get_stock_in_warehouse(warehouse)
            if qty > 0:
                item_info['warehouses'].append({
                    'warehouse': warehouse,
                    'qty': qty
                })
                total_qty += qty
        
        item_info['total_qty'] = total_qty
        if total_qty > 0:
            items_data.append(item_info)
    
    context = {
        'project': project,
        'warehouses': warehouses,
        'items_data': items_data,
    }
    
    return render(request, 'inventory/list.html', context)

def items_list(request):
    """قائمة الأصناف الرئيسية"""
    categories = ItemCategory.objects.filter(is_active=True)
    items = Item.objects.filter(is_active=True).select_related('category')
    
    # فلترة حسب الفئة
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(category_id=category_id)
    
    # بحث
    search = request.GET.get('search')
    if search:
        items = items.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search)
        )
    
    context = {
        'categories': categories,
        'items': items,
        'selected_category': category_id,
    }
    
    # حساب الكميات لكل صنف
    from django.db.models import Q
    for item in items:
        # الكمية الإجمالية في جميع المخازن
        stock_in = StockMove.objects.filter(
            project=project,
            item=item,
            qty_in__gt=0
        ).aggregate(total=Sum('qty_in'))['total'] or Decimal('0')
        
        stock_out = StockMove.objects.filter(
            project=project,
            item=item,
            qty_out__gt=0
        ).aggregate(total=Sum('qty_out'))['total'] or Decimal('0')
        
        item.total_qty = stock_in - stock_out
        item.total_value = item.total_qty * item.std_cost
        
        # حالة المخزون
        if item.total_qty <= 0:
            item.stock_status = 'out'
        elif item.total_qty <= item.min_qty:
            item.stock_status = 'low'
        else:
            item.stock_status = 'available'
        
        # توزيع المخزون على المخازن
        item.warehouse_stock = []
        warehouses = Warehouse.objects.filter(project=project, is_active=True)
        for warehouse in warehouses:
            w_in = StockMove.objects.filter(
                project=project,
                warehouse=warehouse,
                item=item,
                qty_in__gt=0
            ).aggregate(total=Sum('qty_in'))['total'] or Decimal('0')
            
            w_out = StockMove.objects.filter(
                project=project,
                warehouse=warehouse,
                item=item,
                qty_out__gt=0
            ).aggregate(total=Sum('qty_out'))['total'] or Decimal('0')
            
            qty = w_in - w_out
            if qty > 0:
                item.warehouse_stock.append({
                    'warehouse': warehouse.name,
                    'qty': qty
                })
    
    # الإحصائيات
    totals = {
        'items_count': items.count(),
        'total_value': sum(item.total_value for item in items),
        'low_stock_count': sum(1 for item in items if item.stock_status == 'low'),
        'out_of_stock_count': sum(1 for item in items if item.stock_status == 'out'),
    }
    
    # الفئات والمخازن
    categories = ItemCategory.objects.all()
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    
    context = {
        'project': project,
        'items': items,
        'totals': totals,
        'categories': categories,
        'warehouses': warehouses,
    }
    
    return render(request, 'inventory/items.html', context)

def add_item(request, project_id):
    """إضافة صنف جديد"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        uom = request.POST.get('uom', 'piece')
        std_cost = Decimal(request.POST.get('std_cost', '0'))
        min_qty = Decimal(request.POST.get('min_qty', '0'))
        max_qty = Decimal(request.POST.get('max_qty', '0'))
        
        category = get_object_or_404(ItemCategory, id=category_id)
        
        item = Item.objects.create(
            name=name,
            sku=sku,
            category=category,
            uom=uom,
            std_cost=std_cost,
            min_qty=min_qty,
            max_qty=max_qty
        )
        
        messages.success(request, f'تم إضافة الصنف "{name}" بنجاح')
        return redirect('inventory:items', project_id=project.id)
    
    return redirect('inventory:items', project_id=project.id)

def item_movements(request, project_id, item_id):
    """حركات صنف معين"""
    project = get_object_or_404(Project, id=project_id)
    item = get_object_or_404(Item, id=item_id)
    
    movements = StockMove.objects.filter(
        project=project,
        item=item
    ).select_related('warehouse', 'stage').order_by('-move_date')
    
    context = {
        'project': project,
        'item': item,
        'movements': movements,
    }
    
    return render(request, 'inventory/item_movements.html', context)

def receive_stock(request, project_id):
    """استلام مخزون"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        # معالجة الاستلام
        pass
    
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    items = Item.objects.filter(is_active=True)
    
    context = {
        'project': project,
        'warehouses': warehouses,
        'items': items,
    }
    
    return render(request, 'inventory/receive.html', context)

def issue_stock(request, project_id):
    """صرف مواد للمشروع"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse_id')
        item_id = request.POST.get('item_id')
        stage_id = request.POST.get('stage_id')
        qty = Decimal(request.POST.get('qty', '0'))
        notes = request.POST.get('notes', '')
        
        warehouse = get_object_or_404(Warehouse, id=warehouse_id, project=project)
        item = get_object_or_404(Item, id=item_id)
        stage = get_object_or_404(Stage, id=stage_id, project=project) if stage_id else None
        
        # التحقق من توفر المخزون
        available = item.get_stock_in_warehouse(warehouse)
        if qty > available:
            messages.error(request, f'الكمية المتاحة ({available}) غير كافية')
            return redirect('inventory:list', project_id=project.id)
        
        # حساب التكلفة
        unit_cost = item.get_average_cost(project)
        
        try:
            # إنشاء حركة الصرف
            stock_move = StockMove.objects.create(
                project=project,
                warehouse=warehouse,
                item=item,
                qty_out=qty,
                unit_cost=unit_cost,
                stage=stage,
                ref_type='ISSUE',
                move_date=datetime.now().date(),
                notes=notes
            )
            
            messages.success(request, f'تم صرف {qty} {item.get_uom_display()} من {item.name}')
            
            if stage:
                messages.info(request, f'تم إضافة المصروف للمرحلة {stage.name}')
        
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('inventory:list', project_id=project.id)
    
    warehouses = Warehouse.objects.filter(project=project, is_active=True)
    stages = Stage.objects.filter(project=project, status__in=['pending', 'active'])
    items = Item.objects.filter(is_active=True)
    
    context = {
        'project': project,
        'warehouses': warehouses,
        'stages': stages,
        'items': items,
    }
    
    return render(request, 'inventory/issue.html', context)

def stock_movements(request, project_id):
    """حركات المخزون"""
    project = get_object_or_404(Project, id=project_id)
    
    movements = StockMove.objects.filter(
        project=project
    ).select_related('item', 'warehouse', 'stage').order_by('-move_date', '-created_at')
    
    # فلترة
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        movements = movements.filter(warehouse_id=warehouse_id)
    
    item_id = request.GET.get('item')
    if item_id:
        movements = movements.filter(item_id=item_id)
    
    ref_type = request.GET.get('type')
    if ref_type:
        movements = movements.filter(ref_type=ref_type)
    
    # تحديد الفترة
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        movements = movements.filter(move_date__gte=date_from)
    if date_to:
        movements = movements.filter(move_date__lte=date_to)
    
    # المجاميع
    totals = movements.aggregate(
        total_in=Sum('qty_in'),
        total_out=Sum('qty_out'),
        total_value_in=Sum('amount', filter=Q(qty_in__gt=0)),
        total_value_out=Sum('amount', filter=Q(qty_out__gt=0))
    )
    
    warehouses = Warehouse.objects.filter(project=project)
    items = Item.objects.filter(stock_moves__project=project).distinct()
    
    context = {
        'project': project,
        'movements': movements[:100],  # عرض أول 100 حركة
        'warehouses': warehouses,
        'items': items,
        'totals': totals,
        'filters': {
            'warehouse': warehouse_id,
            'item': item_id,
            'type': ref_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'inventory/movements.html', context)