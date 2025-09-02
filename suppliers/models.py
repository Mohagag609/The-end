from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Supplier(models.Model):
    """الموردون (مشتركون على مستوى النظام)"""
    name = models.CharField(max_length=200, verbose_name="اسم المورد")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="الهاتف")
    email = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    tax_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="الرقم الضريبي")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_total_purchases(self, project=None):
        """إجمالي المشتريات من المورد"""
        from purchases.models import PurchaseInvoice
        
        queryset = PurchaseInvoice.objects.filter(supplier=self, status='posted')
        if project:
            queryset = queryset.filter(project=project)
        
        return queryset.aggregate(
            total=models.Sum('total')
        )['total'] or Decimal('0.00')
    
    def get_total_payments(self, project=None):
        """إجمالي المدفوعات للمورد"""
        payments = self.supplier_payments.filter(status='posted')
        if project:
            payments = payments.filter(project=project)
        
        return payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def get_balance(self, project=None):
        """رصيد المورد (المستحق له)"""
        purchases = self.get_total_purchases(project)
        payments = self.get_total_payments(project)
        discounts = self.get_total_discounts(project)
        
        return purchases - payments - discounts
    
    def get_total_discounts(self, project=None):
        """إجمالي الخصومات"""
        discounts = self.supplier_discounts.all()
        if project:
            discounts = discounts.filter(project=project)
        
        return discounts.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

class SupplierPayment(models.Model):
    """مدفوعات الموردين"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('posted', 'مرحّل'),
        ('cancelled', 'ملغي'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('check', 'شيك'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, 
                                related_name='supplier_payments', verbose_name="المورد")
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    payment_date = models.DateField(verbose_name="تاريخ الدفع")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, 
                                     default='cash', verbose_name="طريقة الدفع")
    reference = models.CharField(max_length=100, blank=True, null=True, 
                               verbose_name="المرجع (رقم الشيك/الحوالة)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='draft', verbose_name="الحالة")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "دفعة مورد"
        verbose_name_plural = "دفعات الموردين"
        ordering = ['-payment_date', '-created_at']
        
    def __str__(self):
        return f"{self.supplier.name} - {self.amount} - {self.payment_date}"
    
    def post(self):
        """ترحيل الدفعة"""
        if self.status == 'draft':
            self.status = 'posted'
            self.save()
    
    def cancel(self):
        """إلغاء الدفعة"""
        if self.status == 'posted':
            self.status = 'cancelled'
            self.save()

class SupplierDiscount(models.Model):
    """خصومات الموردين"""
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, 
                                related_name='supplier_discounts', verbose_name="المورد")
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="مبلغ الخصم"
    )
    date = models.DateField(verbose_name="التاريخ")
    reason = models.CharField(max_length=200, verbose_name="سبب الخصم")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "خصم مورد"
        verbose_name_plural = "خصومات الموردين"
        ordering = ['-date', '-created_at']
        
    def __str__(self):
        return f"{self.supplier.name} - {self.amount} - {self.reason}"