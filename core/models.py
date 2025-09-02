from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Currency(models.Model):
    """العملات المستخدمة في النظام"""
    code = models.CharField(max_length=3, unique=True, verbose_name="رمز العملة")
    name = models.CharField(max_length=50, verbose_name="اسم العملة")
    symbol = models.CharField(max_length=5, verbose_name="رمز العملة")
    is_default = models.BooleanField(default=False, verbose_name="العملة الافتراضية")
    
    class Meta:
        verbose_name = "عملة"
        verbose_name_plural = "العملات"
        
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Currency.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class VoucherSequence(models.Model):
    """تسلسل أرقام السندات"""
    VOUCHER_TYPES = [
        ('RECEIPT', 'سند قبض'),
        ('PAYMENT', 'سند صرف'),
        ('PURCHASE', 'فاتورة شراء'),
        ('EXPENSE', 'مصروف'),
    ]
    
    voucher_type = models.CharField(max_length=20, choices=VOUCHER_TYPES, verbose_name="نوع السند")
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, verbose_name="المشروع")
    prefix = models.CharField(max_length=10, verbose_name="البادئة")
    next_number = models.IntegerField(default=1, verbose_name="الرقم التالي")
    year = models.IntegerField(verbose_name="السنة")
    
    class Meta:
        verbose_name = "تسلسل السندات"
        verbose_name_plural = "تسلسلات السندات"
        unique_together = ['voucher_type', 'project', 'year']
        
    def __str__(self):
        return f"{self.prefix}-{self.year}-{self.next_number}"
    
    def get_next_number(self):
        """الحصول على الرقم التالي وتحديث التسلسل"""
        number = f"{self.prefix}-{self.year}-{str(self.next_number).zfill(5)}"
        self.next_number += 1
        self.save()
        return number

class SystemSettings(models.Model):
    """إعدادات النظام العامة"""
    allow_negative_wallet = models.BooleanField(default=False, verbose_name="السماح بالرصيد السالب للمحافظ")
    default_credit_limit = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="حد الائتمان الافتراضي"
    )
    auto_generate_voucher_numbers = models.BooleanField(default=True, verbose_name="توليد أرقام السندات تلقائياً")
    
    class Meta:
        verbose_name = "إعدادات النظام"
        verbose_name_plural = "إعدادات النظام"
        
    def __str__(self):
        return "إعدادات النظام"
    
    def save(self, *args, **kwargs):
        # التأكد من وجود سجل واحد فقط
        self.__class__.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام أو إنشاؤها"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings