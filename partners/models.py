from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import json

class Partner(models.Model):
    """الشركاء"""
    name = models.CharField(max_length=200, verbose_name="اسم الشريك")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="الهاتف")
    email = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "شريك"
        verbose_name_plural = "الشركاء"
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_projects(self):
        """المشروعات التي يشارك فيها"""
        return self.projectpartner_set.all()

class ProjectPartner(models.Model):
    """ربط الشريك بالمشروع ومحفظته"""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, verbose_name="المشروع")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name="الشريك")
    share_pct = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="نسبة الحصة %"
    )
    wallet_balance = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="رصيد المحفظة"
    )
    carry_forward = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="الرصيد المرحّل"
    )
    credit_limit = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="حد الائتمان"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "شريك مشروع"
        verbose_name_plural = "شركاء المشروعات"
        unique_together = ['project', 'partner']
        ordering = ['project', '-share_pct']
        
    def __str__(self):
        return f"{self.partner.name} - {self.project.code} ({self.share_pct}%)"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()
        
        # التحقق من مجموع الحصص
        if self.pk:
            other_shares = ProjectPartner.objects.filter(
                project=self.project
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('share_pct')
            )['total'] or Decimal('0.00')
        else:
            other_shares = ProjectPartner.objects.filter(
                project=self.project
            ).aggregate(
                total=models.Sum('share_pct')
            )['total'] or Decimal('0.00')
        
        total_shares = other_shares + self.share_pct
        
        if total_shares > Decimal('100.00'):
            raise ValidationError(
                f"مجموع الحصص ({total_shares}%) يتجاوز 100%. الحصص الحالية: {other_shares}%"
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_total_receipts(self):
        """إجمالي المقبوضات"""
        return self.vouchers.filter(type='receipt').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def get_total_payments(self):
        """إجمالي المدفوعات"""
        return self.vouchers.filter(type='payment').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def update_wallet_balance(self):
        """تحديث رصيد المحفظة"""
        receipts = self.get_total_receipts()
        payments = self.get_total_payments()
        self.wallet_balance = receipts - payments
        self.save(update_fields=['wallet_balance'])
    
    def can_withdraw(self, amount):
        """التحقق من إمكانية السحب"""
        from core.models import SystemSettings
        settings = SystemSettings.get_settings()
        
        if settings.allow_negative_wallet:
            available = self.wallet_balance + self.credit_limit
        else:
            available = self.wallet_balance
        
        return amount <= available

class Voucher(models.Model):
    """سندات القبض والصرف"""
    VOUCHER_TYPES = [
        ('receipt', 'سند قبض'),
        ('payment', 'سند صرف'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, verbose_name="المشروع")
    type = models.CharField(max_length=10, choices=VOUCHER_TYPES, verbose_name="نوع السند")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name="الشريك")
    project_partner = models.ForeignKey(ProjectPartner, on_delete=models.CASCADE, 
                                       related_name='vouchers', verbose_name="محفظة الشريك")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    date = models.DateField(verbose_name="التاريخ")
    ref_no = models.CharField(max_length=50, verbose_name="رقم السند")
    description = models.TextField(blank=True, null=True, verbose_name="البيان")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    attachment = models.FileField(upload_to='vouchers/', blank=True, null=True, verbose_name="المرفق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    created_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="أنشأ بواسطة")
    
    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "السندات"
        ordering = ['-date', '-created_at']
        unique_together = ['project', 'ref_no']
        
    def __str__(self):
        return f"{self.get_type_display()} - {self.ref_no} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # التحقق من إمكانية الصرف
        if self.type == 'payment' and not self.pk:
            if not self.project_partner.can_withdraw(self.amount):
                raise ValidationError("الرصيد غير كافي للصرف")
        
        # توليد رقم السند تلقائياً
        if not self.ref_no:
            from core.models import VoucherSequence
            from datetime import datetime
            
            year = datetime.now().year
            voucher_type = 'RECEIPT' if self.type == 'receipt' else 'PAYMENT'
            prefix = 'REC' if self.type == 'receipt' else 'PAY'
            
            sequence, created = VoucherSequence.objects.get_or_create(
                voucher_type=voucher_type,
                project=self.project,
                year=year,
                defaults={'prefix': prefix}
            )
            self.ref_no = sequence.get_next_number()
        
        super().save(*args, **kwargs)
        
        # تحديث رصيد المحفظة
        self.project_partner.update_wallet_balance()

class WalletPriority(models.Model):
    """أولوية الخصم من المحافظ (للخصم المتسلسل)"""
    project = models.OneToOneField('projects.Project', on_delete=models.CASCADE, 
                                  related_name='wallet_priority', verbose_name="المشروع")
    ordered_partner_ids = models.JSONField(default=list, verbose_name="ترتيب الشركاء")
    allow_negative = models.BooleanField(default=False, verbose_name="السماح بالرصيد السالب")
    credit_limit_per_partner = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="حد الائتمان لكل شريك"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "أولوية الخصم"
        verbose_name_plural = "أولويات الخصم"
        
    def __str__(self):
        return f"أولوية الخصم - {self.project.code}"
    
    def get_ordered_wallets(self):
        """الحصول على المحافظ مرتبة حسب الأولوية"""
        if not self.ordered_partner_ids:
            return ProjectPartner.objects.filter(project=self.project).order_by('-share_pct')
        
        wallets = []
        for partner_id in self.ordered_partner_ids:
            try:
                wallet = ProjectPartner.objects.get(
                    project=self.project, 
                    partner_id=partner_id
                )
                wallets.append(wallet)
            except ProjectPartner.DoesNotExist:
                continue
        
        # إضافة أي محافظ غير موجودة في الترتيب
        existing_ids = [w.partner_id for w in wallets]
        remaining = ProjectPartner.objects.filter(
            project=self.project
        ).exclude(partner_id__in=existing_ids)
        
        wallets.extend(list(remaining))
        return wallets
    
    def cascade_debit(self, amount, description=""):
        """الخصم المتسلسل من المحافظ"""
        from decimal import Decimal
        
        wallets = self.get_ordered_wallets()
        remaining = amount
        debit_details = []
        
        for wallet in wallets:
            if remaining <= 0:
                break
            
            if self.allow_negative:
                available = wallet.wallet_balance + wallet.credit_limit
            else:
                available = wallet.wallet_balance
            
            if available <= 0:
                continue
            
            take = min(available, remaining)
            
            # إنشاء سند صرف
            voucher = Voucher.objects.create(
                project=self.project,
                type='payment',
                partner=wallet.partner,
                project_partner=wallet,
                amount=take,
                date=models.functions.Now(),
                description=f"خصم متسلسل: {description}"
            )
            
            debit_details.append({
                'partner': wallet.partner.name,
                'amount': float(take),
                'voucher_id': voucher.id
            })
            
            remaining -= take
        
        if remaining > 0:
            # لم يتم خصم المبلغ بالكامل
            return {
                'success': False,
                'debited': float(amount - remaining),
                'remaining': float(remaining),
                'details': debit_details
            }
        
        return {
            'success': True,
            'debited': float(amount),
            'remaining': 0,
            'details': debit_details
        }