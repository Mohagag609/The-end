from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class ItemCategory(models.Model):
    """فئات الأصناف"""
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم الفئة")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "فئة صنف"
        verbose_name_plural = "فئات الأصناف"
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Item(models.Model):
    """الأصناف (مشتركة على مستوى النظام)"""
    UNIT_CHOICES = [
        ('PC', 'قطعة'),
        ('KG', 'كيلوجرام'),
        ('TON', 'طن'),
        ('M', 'متر'),
        ('M2', 'متر مربع'),
        ('M3', 'متر مكعب'),
        ('L', 'لتر'),
        ('BOX', 'كرتونة'),
        ('PACK', 'عبوة'),
    ]
    
    sku = models.CharField(max_length=50, unique=True, verbose_name="كود الصنف")
    name = models.CharField(max_length=200, verbose_name="اسم الصنف")
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT, 
                                related_name='items', verbose_name="الفئة")
    uom = models.CharField(max_length=10, choices=UNIT_CHOICES, 
                          default='PC', verbose_name="وحدة القياس")
    std_cost = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="التكلفة القياسية"
    )
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    min_stock = models.DecimalField(
        max_digits=14, 
        decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="الحد الأدنى للمخزون"
    )
    max_stock = models.DecimalField(
        max_digits=14, 
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="الحد الأقصى للمخزون"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "صنف"
        verbose_name_plural = "الأصناف"
        ordering = ['category', 'name']
        
    def __str__(self):
        return f"{self.sku} - {self.name}"
    
    def get_stock_in_warehouse(self, warehouse):
        """رصيد الصنف في مخزن محدد"""
        moves = StockMove.objects.filter(item=self, warehouse=warehouse)
        
        totals = moves.aggregate(
            total_in=models.Sum('qty_in'),
            total_out=models.Sum('qty_out')
        )
        
        qty_in = totals['total_in'] or Decimal('0.000')
        qty_out = totals['total_out'] or Decimal('0.000')
        
        return qty_in - qty_out
    
    def get_total_stock(self, project=None):
        """إجمالي رصيد الصنف"""
        moves = StockMove.objects.filter(item=self)
        
        if project:
            moves = moves.filter(project=project)
        
        totals = moves.aggregate(
            total_in=models.Sum('qty_in'),
            total_out=models.Sum('qty_out')
        )
        
        qty_in = totals['total_in'] or Decimal('0.000')
        qty_out = totals['total_out'] or Decimal('0.000')
        
        return qty_in - qty_out
    
    def get_average_cost(self, project=None):
        """حساب متوسط التكلفة المرجح"""
        moves = StockMove.objects.filter(item=self, qty_in__gt=0)
        
        if project:
            moves = moves.filter(project=project)
        
        total_qty = Decimal('0.000')
        total_value = Decimal('0.00')
        
        for move in moves:
            total_qty += move.qty_in
            total_value += move.qty_in * move.unit_cost
        
        if total_qty > 0:
            return total_value / total_qty
        
        return self.std_cost

class StockMove(models.Model):
    """حركات المخزون"""
    REF_TYPES = [
        ('PI', 'فاتورة شراء'),
        ('ISSUE', 'صرف مواد'),
        ('ADJUST', 'تسوية'),
        ('TRANSFER', 'تحويل'),
        ('RETURN', 'مرتجع'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    warehouse = models.ForeignKey('projects.Warehouse', on_delete=models.CASCADE, 
                                 verbose_name="المخزن")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, 
                            related_name='stock_moves', verbose_name="الصنف")
    qty_in = models.DecimalField(
        max_digits=14, 
        decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="الكمية الواردة"
    )
    qty_out = models.DecimalField(
        max_digits=14, 
        decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="الكمية الصادرة"
    )
    unit_cost = models.DecimalField(
        max_digits=14, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000'))],
        verbose_name="تكلفة الوحدة"
    )
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="القيمة"
    )
    stage = models.ForeignKey('projects.Stage', on_delete=models.SET_NULL, 
                             null=True, blank=True, verbose_name="المرحلة")
    ref_type = models.CharField(max_length=10, choices=REF_TYPES, verbose_name="نوع المرجع")
    ref_id = models.IntegerField(null=True, blank=True, verbose_name="رقم المرجع")
    move_date = models.DateField(verbose_name="تاريخ الحركة")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    created_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="أنشأ بواسطة")
    
    class Meta:
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"
        ordering = ['-move_date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'item', 'move_date']),
            models.Index(fields=['warehouse', 'item']),
            models.Index(fields=['ref_type', 'ref_id']),
        ]
        
    def __str__(self):
        direction = "وارد" if self.qty_in > 0 else "صادر"
        qty = self.qty_in if self.qty_in > 0 else self.qty_out
        return f"{direction} - {self.item.name} - {qty} {self.item.get_uom_display()}"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()
        
        # التحقق من أن إحدى الكميات فقط أكبر من صفر
        if self.qty_in > 0 and self.qty_out > 0:
            raise ValidationError("لا يمكن أن تكون الكمية الواردة والصادرة موجبة في نفس الحركة")
        
        if self.qty_in == 0 and self.qty_out == 0:
            raise ValidationError("يجب تحديد كمية واردة أو صادرة")
        
        # التحقق من توفر المخزون عند الصرف
        if self.qty_out > 0 and not self.pk:
            available = self.item.get_stock_in_warehouse(self.warehouse)
            if available < self.qty_out:
                raise ValidationError(
                    f"الكمية المتاحة ({available}) غير كافية للصرف ({self.qty_out})"
                )
    
    def save(self, *args, **kwargs):
        # حساب القيمة
        if self.qty_in > 0:
            self.amount = (self.qty_in * self.unit_cost).quantize(Decimal('0.01'))
        else:
            self.amount = (self.qty_out * self.unit_cost).quantize(Decimal('0.01'))
        
        # استخدام التكلفة القياسية إذا لم تحدد
        if self.unit_cost == 0:
            self.unit_cost = self.item.std_cost
            self.amount = ((self.qty_in or self.qty_out) * self.unit_cost).quantize(Decimal('0.01'))
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # إنشاء مصروف تلقائي عند صرف المواد للمرحلة
        if self.ref_type == 'ISSUE' and self.stage and self.qty_out > 0:
            from expenses.models import Expense
            
            Expense.objects.get_or_create(
                project=self.project,
                stage=self.stage,
                date=self.move_date,
                amount=self.amount,
                payee_type='stock',
                payee_id=self.id,
                defaults={
                    'description': f"صرف مواد: {self.item.name} - {self.qty_out} {self.item.get_uom_display()}"
                }
            )
    
    @classmethod
    def get_available_qty(cls, project, warehouse, item):
        """حساب الكمية المتاحة لصنف في مخزن"""
        from django.db.models import Sum
        from decimal import Decimal
        
        movements = cls.objects.filter(
            project=project,
            warehouse=warehouse,
            item=item
        )
        
        qty_in = movements.filter(qty_in__gt=0).aggregate(
            total=Sum('qty_in')
        )['total'] or Decimal('0')
        
        qty_out = movements.filter(qty_out__gt=0).aggregate(
            total=Sum('qty_out')
        )['total'] or Decimal('0')
        
        return qty_in - qty_out