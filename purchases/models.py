from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class PurchaseInvoice(models.Model):
    """فواتير الشراء"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('posted', 'مرحّل'),
        ('cancelled', 'ملغي'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, 
                                verbose_name="المورد")
    invoice_no = models.CharField(max_length=50, verbose_name="رقم الفاتورة")
    date = models.DateField(verbose_name="تاريخ الفاتورة")
    due_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستحقاق")
    subtotal = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="المجموع الفرعي"
    )
    tax_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الضريبة"
    )
    discount_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الخصم"
    )
    total = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الإجمالي"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='draft', verbose_name="الحالة")
    attachment = models.FileField(upload_to='purchases/', blank=True, null=True, 
                                verbose_name="المرفق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الترحيل")
    
    class Meta:
        verbose_name = "فاتورة شراء"
        verbose_name_plural = "فواتير الشراء"
        ordering = ['-date', '-created_at']
        unique_together = ['project', 'supplier', 'invoice_no']
        indexes = [
            models.Index(fields=['project', 'date']),
            models.Index(fields=['supplier', 'status']),
        ]
        
    def __str__(self):
        return f"{self.invoice_no} - {self.supplier.name} - {self.total}"
    
    def calculate_totals(self):
        """حساب المجاميع من البنود"""
        items = self.items.all()
        
        self.subtotal = sum(item.line_total for item in items)
        self.tax_amount = sum(item.tax for item in items)
        self.total = self.subtotal + self.tax_amount - self.discount_amount
        
        self.save(update_fields=['subtotal', 'tax_amount', 'total'])
    
    def can_post(self):
        """التحقق من إمكانية الترحيل"""
        if self.status != 'draft':
            return False
        
        if not self.items.exists():
            return False
        
        return True
    
    def post(self):
        """ترحيل الفاتورة وإنشاء حركات المخزون"""
        if not self.can_post():
            raise ValidationError("لا يمكن ترحيل الفاتورة")
        
        from inventory.models import StockMove
        from django.utils import timezone
        
        # إنشاء حركات المخزون لكل بند
        for item in self.items.all():
            # الحصول على المخزن الافتراضي للمشروع
            warehouse = self.project.warehouses.filter(is_active=True).first()
            if not warehouse:
                raise ValidationError("لا يوجد مخزن نشط للمشروع")
            
            StockMove.objects.create(
                project=self.project,
                warehouse=warehouse,
                item=item.item,
                qty_in=item.qty,
                unit_cost=item.unit_cost,
                ref_type='PI',
                ref_id=self.id,
                move_date=self.date,
                notes=f"فاتورة شراء: {self.invoice_no}"
            )
        
        self.status = 'posted'
        self.posted_at = timezone.now()
        self.save()
    
    def cancel(self):
        """إلغاء الفاتورة"""
        if self.status != 'posted':
            raise ValidationError("يمكن إلغاء الفواتير المرحّلة فقط")
        
        # حذف حركات المخزون المرتبطة
        from inventory.models import StockMove
        StockMove.objects.filter(ref_type='PI', ref_id=self.id).delete()
        
        self.status = 'cancelled'
        self.save()

class PurchaseItem(models.Model):
    """بنود فاتورة الشراء"""
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, 
                               related_name='items', verbose_name="الفاتورة")
    item = models.ForeignKey('inventory.Item', on_delete=models.CASCADE, 
                            verbose_name="الصنف")
    qty = models.DecimalField(
        max_digits=14, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="الكمية"
    )
    unit_cost = models.DecimalField(
        max_digits=14, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name="سعر الوحدة"
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="نسبة الضريبة %"
    )
    tax = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الضريبة"
    )
    line_total = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="إجمالي السطر"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "بند فاتورة شراء"
        verbose_name_plural = "بنود فواتير الشراء"
        ordering = ['invoice', 'created_at']
        
    def __str__(self):
        return f"{self.item.name} - {self.qty} × {self.unit_cost}"
    
    def save(self, *args, **kwargs):
        # حساب الضريبة والإجمالي
        subtotal = self.qty * self.unit_cost
        self.tax = subtotal * (self.tax_rate / Decimal('100'))
        self.line_total = subtotal + self.tax
        
        super().save(*args, **kwargs)
        
        # تحديث مجاميع الفاتورة
        if self.invoice_id:
            self.invoice.calculate_totals()

class PurchaseReturn(models.Model):
    """مرتجعات المشتريات"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('posted', 'مرحّل'),
        ('cancelled', 'ملغي'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, 
                                verbose_name="المورد")
    original_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL, 
                                        null=True, blank=True,
                                        related_name='returns',
                                        verbose_name="الفاتورة الأصلية")
    return_no = models.CharField(max_length=50, verbose_name="رقم المرتجع")
    date = models.DateField(verbose_name="تاريخ المرتجع")
    total = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الإجمالي"
    )
    reason = models.TextField(verbose_name="سبب المرتجع")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='draft', verbose_name="الحالة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "مرتجع شراء"
        verbose_name_plural = "مرتجعات الشراء"
        ordering = ['-date', '-created_at']
        unique_together = ['project', 'return_no']
        
    def __str__(self):
        return f"{self.return_no} - {self.supplier.name} - {self.total}"