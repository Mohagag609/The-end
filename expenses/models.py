from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Expense(models.Model):
    """المصروفات"""
    PAYEE_TYPES = [
        ('supplier', 'مورد'),
        ('partner', 'شريك'),
        ('stock', 'صرف مواد'),
        ('employee', 'موظف'),
        ('contractor', 'مقاول'),
        ('other', 'أخرى'),
    ]
    
    EXPENSE_CATEGORIES = [
        ('labor', 'عمالة'),
        ('transport', 'نقل'),
        ('utilities', 'مرافق'),
        ('rent', 'إيجار'),
        ('maintenance', 'صيانة'),
        ('admin', 'إدارية'),
        ('materials', 'مواد'),
        ('other', 'أخرى'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    stage = models.ForeignKey('projects.Stage', on_delete=models.SET_NULL, 
                             null=True, blank=True,
                             related_name='expenses',
                             verbose_name="المرحلة")
    date = models.DateField(verbose_name="التاريخ")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES, 
                              default='other', verbose_name="الفئة")
    payee_type = models.CharField(max_length=20, choices=PAYEE_TYPES, 
                                 verbose_name="نوع المستفيد")
    payee_id = models.IntegerField(null=True, blank=True, verbose_name="رقم المستفيد")
    payee_name = models.CharField(max_length=200, blank=True, null=True, 
                                 verbose_name="اسم المستفيد")
    description = models.TextField(verbose_name="البيان")
    reference = models.CharField(max_length=100, blank=True, null=True, 
                               verbose_name="المرجع")
    attachment = models.FileField(upload_to='expenses/', blank=True, null=True, 
                                verbose_name="المرفق")
    is_allocated = models.BooleanField(default=False, verbose_name="تم التوزيع")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    created_by = models.CharField(max_length=100, blank=True, null=True, 
                                 verbose_name="أنشأ بواسطة")
    
    class Meta:
        verbose_name = "مصروف"
        verbose_name_plural = "المصروفات"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'date']),
            models.Index(fields=['stage', 'is_allocated']),
            models.Index(fields=['payee_type', 'payee_id']),
        ]
        
    def __str__(self):
        return f"{self.description} - {self.amount} - {self.date}"
    
    def get_payee_display(self):
        """عرض اسم المستفيد"""
        if self.payee_name:
            return self.payee_name
        
        if self.payee_type == 'supplier':
            from suppliers.models import Supplier
            try:
                supplier = Supplier.objects.get(id=self.payee_id)
                return supplier.name
            except Supplier.DoesNotExist:
                pass
        
        elif self.payee_type == 'partner':
            from partners.models import Partner
            try:
                partner = Partner.objects.get(id=self.payee_id)
                return partner.name
            except Partner.DoesNotExist:
                pass
        
        elif self.payee_type == 'stock':
            return "صرف مواد"
        
        return self.get_payee_type_display()
    
    def save(self, *args, **kwargs):
        # حفظ اسم المستفيد للبحث السريع
        if not self.payee_name:
            self.payee_name = self.get_payee_display()
        
        super().save(*args, **kwargs)

class RecurringExpense(models.Model):
    """المصروفات الدورية"""
    FREQUENCY_CHOICES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('yearly', 'سنوي'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    stage = models.ForeignKey('projects.Stage', on_delete=models.SET_NULL, 
                             null=True, blank=True,
                             verbose_name="المرحلة")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    category = models.CharField(max_length=20, choices=Expense.EXPENSE_CATEGORIES, 
                              default='other', verbose_name="الفئة")
    description = models.TextField(verbose_name="البيان")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, 
                               verbose_name="التكرار")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ النهاية")
    next_date = models.DateField(verbose_name="التاريخ التالي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    last_generated = models.DateField(null=True, blank=True, 
                                     verbose_name="آخر توليد")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "مصروف دوري"
        verbose_name_plural = "المصروفات الدورية"
        ordering = ['next_date', 'project']
        
    def __str__(self):
        return f"{self.description} - {self.amount} - {self.get_frequency_display()}"
    
    def generate_expense(self):
        """توليد المصروف للفترة الحالية"""
        from datetime import timedelta
        from django.utils import timezone
        
        if not self.is_active:
            return None
        
        if self.end_date and self.next_date > self.end_date:
            self.is_active = False
            self.save()
            return None
        
        # إنشاء المصروف
        expense = Expense.objects.create(
            project=self.project,
            stage=self.stage,
            date=self.next_date,
            amount=self.amount,
            category=self.category,
            payee_type='other',
            description=f"{self.description} (دوري)",
            reference=f"RECURRING-{self.id}"
        )
        
        # تحديث التاريخ التالي
        if self.frequency == 'daily':
            self.next_date += timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_date += timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # إضافة شهر
            month = self.next_date.month + 1
            year = self.next_date.year
            if month > 12:
                month = 1
                year += 1
            self.next_date = self.next_date.replace(month=month, year=year)
        elif self.frequency == 'quarterly':
            # إضافة 3 أشهر
            month = self.next_date.month + 3
            year = self.next_date.year
            if month > 12:
                month -= 12
                year += 1
            self.next_date = self.next_date.replace(month=month, year=year)
        elif self.frequency == 'yearly':
            self.next_date = self.next_date.replace(year=self.next_date.year + 1)
        
        self.last_generated = timezone.now().date()
        self.save()
        
        return expense