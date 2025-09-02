from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Project(models.Model):
    """المشروعات"""
    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('closed', 'مغلق'),
    ]
    
    code = models.CharField(max_length=20, unique=True, verbose_name="كود المشروع")
    name = models.CharField(max_length=200, verbose_name="اسم المشروع")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    currency = models.ForeignKey('core.Currency', on_delete=models.PROTECT, 
                                default=1, verbose_name="العملة")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='open', verbose_name="الحالة")
    start_date = models.DateField(null=True, blank=True, verbose_name="تاريخ البداية")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ النهاية")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "مشروع"
        verbose_name_plural = "المشروعات"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_total_cost(self):
        """حساب إجمالي تكلفة المشروع"""
        from expenses.models import Expense
        from inventory.models import StockMove
        
        expenses_total = Expense.objects.filter(project=self).aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        stock_issues_total = StockMove.objects.filter(
            project=self, 
            qty_out__gt=0
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        return expenses_total + stock_issues_total
    
    def get_partners_summary(self):
        """ملخص الشركاء في المشروع"""
        return self.projectpartner_set.all()
    
    def validate_partners_shares(self):
        """التحقق من أن مجموع حصص الشركاء = 100%"""
        total_share = self.projectpartner_set.aggregate(
            total=models.Sum('share_pct'))['total'] or Decimal('0.00')
        return total_share == Decimal('100.00')

class Stage(models.Model):
    """المراحل"""
    STATUS_CHOICES = [
        ('pending', 'لم تبدأ'),
        ('active', 'نشطة'),
        ('completed', 'مكتملة'),
        ('suspended', 'معلقة'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, 
                               related_name='stages', verbose_name="المشروع")
    name = models.CharField(max_length=200, verbose_name="اسم المرحلة")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    budget = models.DecimalField(max_digits=14, decimal_places=2, 
                                default=Decimal('0.00'),
                                validators=[MinValueValidator(Decimal('0.00'))],
                                verbose_name="الميزانية")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='pending', verbose_name="الحالة")
    start_date = models.DateField(null=True, blank=True, verbose_name="تاريخ البداية")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ النهاية")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "مرحلة"
        verbose_name_plural = "المراحل"
        ordering = ['project', 'created_at']
        
    def __str__(self):
        return f"{self.project.code} - {self.name}"
    
    def get_total_cost(self):
        """حساب إجمالي تكلفة المرحلة"""
        from expenses.models import Expense
        from inventory.models import StockMove
        
        expenses_total = Expense.objects.filter(stage=self).aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        stock_issues_total = StockMove.objects.filter(
            stage=self, 
            qty_out__gt=0
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        return expenses_total + stock_issues_total
    
    def get_allocated_amount(self):
        """المبلغ الموزع على الشركاء"""
        from allocations.models import Allocation
        
        return Allocation.objects.filter(
            stage=self, 
            posted=True
        ).aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
    
    def get_delta(self):
        """حساب الفرق بين التكلفة والموزع (Delta)"""
        total_cost = self.get_total_cost()
        allocated = self.get_allocated_amount()
        delta = total_cost - allocated
        return delta if delta > 0 else Decimal('0.00')
    
    def is_over_budget(self):
        """التحقق من تجاوز الميزانية"""
        return self.get_total_cost() > self.budget

class Warehouse(models.Model):
    """المخازن"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, 
                               related_name='warehouses', verbose_name="المشروع")
    name = models.CharField(max_length=200, verbose_name="اسم المخزن")
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="الموقع")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "مخزن"
        verbose_name_plural = "المخازن"
        ordering = ['project', 'name']
        
    def __str__(self):
        return f"{self.project.code} - {self.name}"
    
    def get_stock_balance(self, item=None):
        """الحصول على رصيد المخزون"""
        from inventory.models import StockMove
        
        queryset = StockMove.objects.filter(warehouse=self)
        if item:
            queryset = queryset.filter(item=item)
        
        totals = queryset.aggregate(
            total_in=models.Sum('qty_in'),
            total_out=models.Sum('qty_out')
        )
        
        qty_in = totals['total_in'] or Decimal('0.000')
        qty_out = totals['total_out'] or Decimal('0.000')
        
        return qty_in - qty_out