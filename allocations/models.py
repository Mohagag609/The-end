from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import json

class Allocation(models.Model):
    """توزيع التكاليف على الشركاء"""
    RULE_CHOICES = [
        ('by_share', 'حسب الحصة'),
        ('custom', 'مخصص'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, 
                               verbose_name="المشروع")
    stage = models.ForeignKey('projects.Stage', on_delete=models.CASCADE,
                             related_name='allocations',
                             verbose_name="المرحلة")
    rule = models.CharField(max_length=10, choices=RULE_CHOICES, 
                          default='by_share', verbose_name="قاعدة التوزيع")
    details_json = models.JSONField(default=dict, verbose_name="تفاصيل التوزيع")
    total_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ الإجمالي"
    )
    posted = models.BooleanField(default=False, verbose_name="مرحّل")
    alloc_date = models.DateField(verbose_name="تاريخ التوزيع")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الترحيل")
    created_by = models.CharField(max_length=100, blank=True, null=True, 
                                 verbose_name="أنشأ بواسطة")
    
    class Meta:
        verbose_name = "توزيع تكاليف"
        verbose_name_plural = "توزيعات التكاليف"
        ordering = ['-alloc_date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'stage', 'posted']),
            models.Index(fields=['alloc_date']),
        ]
        
    def __str__(self):
        status = "مرحّل" if self.posted else "مسودة"
        return f"{self.stage.name} - {self.total_amount} - {status}"
    
    def calculate_delta(self):
        """حساب الفرق (Delta) للمرحلة"""
        return self.stage.get_delta()
    
    def prepare_allocation(self):
        """تحضير التوزيع حسب القاعدة"""
        from partners.models import ProjectPartner
        
        if self.rule == 'by_share':
            # توزيع حسب حصص الشركاء
            partners = ProjectPartner.objects.filter(project=self.project)
            details = {}
            
            for partner in partners:
                share_amount = self.total_amount * (partner.share_pct / Decimal('100'))
                # التقريب إلى قرشين
                share_amount = share_amount.quantize(Decimal('0.01'))
                details[str(partner.partner.id)] = {
                    'partner_id': partner.partner.id,
                    'partner_name': partner.partner.name,
                    'share_pct': float(partner.share_pct),
                    'amount': float(share_amount)
                }
            
            self.details_json = details
        
        # للتوزيع المخصص، يتم تحديد التفاصيل يدوياً
        
        return self.details_json
    
    def validate_allocation(self):
        """التحقق من صحة التوزيع"""
        if not self.details_json:
            raise ValidationError("لا توجد تفاصيل للتوزيع")
        
        # التحقق من مجموع المبالغ
        total = Decimal('0.00')
        for detail in self.details_json.values():
            total += Decimal(str(detail.get('amount', 0)))
        
        # السماح بفرق بسيط بسبب التقريب
        diff = abs(total - self.total_amount)
        if diff > Decimal('0.10'):  # السماح بفرق 10 قروش كحد أقصى
            raise ValidationError(
                f"مجموع التوزيع ({total}) لا يساوي المبلغ الإجمالي ({self.total_amount})"
            )
        
        # التحقق من توفر الأرصدة
        from partners.models import ProjectPartner
        
        for detail in self.details_json.values():
            partner_id = detail.get('partner_id')
            amount = Decimal(str(detail.get('amount', 0)))
            
            try:
                project_partner = ProjectPartner.objects.get(
                    project=self.project,
                    partner_id=partner_id
                )
                
                if not project_partner.can_withdraw(amount):
                    raise ValidationError(
                        f"رصيد الشريك {project_partner.partner.name} غير كافي ({project_partner.wallet_balance})"
                    )
            except ProjectPartner.DoesNotExist:
                raise ValidationError(f"الشريك {partner_id} غير موجود في المشروع")
    
    def post(self):
        """ترحيل التوزيع وخصم المبالغ من محافظ الشركاء"""
        if self.posted:
            raise ValidationError("التوزيع مرحّل بالفعل")
        
        self.validate_allocation()
        
        from partners.models import Voucher, ProjectPartner
        from django.utils import timezone
        
        # خصم المبالغ من محافظ الشركاء
        for detail in self.details_json.values():
            partner_id = detail.get('partner_id')
            amount = Decimal(str(detail.get('amount', 0)))
            
            if amount <= 0:
                continue
            
            project_partner = ProjectPartner.objects.get(
                project=self.project,
                partner_id=partner_id
            )
            
            # إنشاء سند صرف
            Voucher.objects.create(
                project=self.project,
                type='payment',
                partner=project_partner.partner,
                project_partner=project_partner,
                amount=amount,
                date=self.alloc_date,
                description=f"توزيع تكاليف المرحلة: {self.stage.name}"
            )
        
        # تحديث حالة المصروفات المرتبطة
        from expenses.models import Expense
        Expense.objects.filter(
            stage=self.stage,
            is_allocated=False
        ).update(is_allocated=True)
        
        self.posted = True
        self.posted_at = timezone.now()
        self.save()
    
    def reverse(self):
        """عكس التوزيع"""
        if not self.posted:
            raise ValidationError("التوزيع غير مرحّل")
        
        from partners.models import Voucher
        from django.utils import timezone
        
        # إنشاء سندات قبض عكسية
        for detail in self.details_json.values():
            partner_id = detail.get('partner_id')
            amount = Decimal(str(detail.get('amount', 0)))
            
            if amount <= 0:
                continue
            
            from partners.models import ProjectPartner
            project_partner = ProjectPartner.objects.get(
                project=self.project,
                partner_id=partner_id
            )
            
            Voucher.objects.create(
                project=self.project,
                type='receipt',
                partner=project_partner.partner,
                project_partner=project_partner,
                amount=amount,
                date=timezone.now().date(),
                description=f"عكس توزيع تكاليف المرحلة: {self.stage.name}"
            )
        
        # تحديث حالة المصروفات
        from expenses.models import Expense
        Expense.objects.filter(
            stage=self.stage,
            is_allocated=True,
            date__lte=self.alloc_date
        ).update(is_allocated=False)
        
        self.posted = False
        self.posted_at = None
        self.save()

class AllocationLine(models.Model):
    """تفاصيل سطور التوزيع (اختياري للتقارير)"""
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE,
                                  related_name='lines',
                                  verbose_name="التوزيع")
    partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE,
                               verbose_name="الشريك")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="المبلغ"
    )
    share_pct = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="نسبة الحصة %"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سطر توزيع"
        verbose_name_plural = "سطور التوزيع"
        ordering = ['allocation', '-amount']
        
    def __str__(self):
        return f"{self.partner.name} - {self.amount}"