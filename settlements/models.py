from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class PartnerSettleBatch(models.Model):
    """دفعات التسوية بين الشركاء"""
    STATUS_CHOICES = [
        ('open', 'مفتوحة'),
        ('posted', 'مرحّلة'),
        ('reversed', 'معكوسة'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                               verbose_name="المشروع")
    cutoff_date = models.DateField(verbose_name="تاريخ القطع")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                            default='open', verbose_name="الحالة")
    total_cost_until_cutoff = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="إجمالي التكلفة حتى تاريخ القطع"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الترحيل")
    reversed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ العكس")
    created_by = models.CharField(max_length=100, blank=True, null=True,
                                 verbose_name="أنشأ بواسطة")
    
    class Meta:
        verbose_name = "دفعة تسوية"
        verbose_name_plural = "دفعات التسوية"
        ordering = ['-cutoff_date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'cutoff_date']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.project.code} - {self.cutoff_date} - {self.get_status_display()}"
    
    def calculate_total_cost(self):
        """حساب إجمالي تكلفة المشروع حتى تاريخ القطع"""
        from expenses.models import Expense
        from inventory.models import StockMove
        
        # مصروفات حتى تاريخ القطع
        expenses_total = Expense.objects.filter(
            project=self.project,
            date__lte=self.cutoff_date
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # صرف مواد حتى تاريخ القطع
        stock_issues_total = StockMove.objects.filter(
            project=self.project,
            qty_out__gt=0,
            move_date__lte=self.cutoff_date
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self.total_cost_until_cutoff = expenses_total + stock_issues_total
        return self.total_cost_until_cutoff
    
    def prepare_settlement(self):
        """تحضير التسوية وحساب الفروقات"""
        from partners.models import ProjectPartner, Voucher
        
        # حساب إجمالي التكلفة
        total_cost = self.calculate_total_cost()
        
        # حذف السطور القديمة إن وجدت
        self.lines.all().delete()
        
        # إنشاء سطور التسوية لكل شريك
        partners = ProjectPartner.objects.filter(project=self.project)
        
        for partner in partners:
            # ما يجب أن يتحمله الشريك
            should_bear = total_cost * (partner.share_pct / Decimal('100'))
            should_bear = should_bear.quantize(Decimal('0.01'))
            
            # ما دفعه الشريك فعلاً (إيداعات - سحوبات)
            receipts = Voucher.objects.filter(
                project_partner=partner,
                type='receipt',
                date__lte=self.cutoff_date
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            
            payments = Voucher.objects.filter(
                project_partner=partner,
                type='payment',
                date__lte=self.cutoff_date
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            
            actually_paid = receipts - payments
            
            # إضافة الرصيد المرحّل
            actually_paid += partner.carry_forward
            
            # الفرق (موجب = له، سالب = عليه)
            diff = actually_paid - should_bear
            
            # إنشاء سطر التسوية
            PartnerSettleLine.objects.create(
                batch=self,
                partner=partner.partner,
                project_partner=partner,
                share_pct_at_cutoff=partner.share_pct,
                should_bear=should_bear,
                actually_paid=actually_paid,
                diff=diff
            )
        
        self.save()
        return self.lines.all()
    
    def generate_claims(self):
        """توليد المطالبات بين الشركاء"""
        if self.status != 'open':
            raise ValidationError("يمكن توليد المطالبات للدفعات المفتوحة فقط")
        
        # حذف المطالبات القديمة
        self.claims.all().delete()
        
        # تجميع الدائنين والمدينين
        creditors = []  # لهم فلوس
        debtors = []    # عليهم فلوس
        
        for line in self.lines.all():
            if line.diff > 0:
                creditors.append({
                    'partner': line.partner,
                    'amount': line.diff
                })
            elif line.diff < 0:
                debtors.append({
                    'partner': line.partner,
                    'amount': abs(line.diff)
                })
        
        # مطابقة Greedy للمطالبات
        for debtor in debtors:
            remaining = debtor['amount']
            
            for creditor in creditors:
                if remaining <= 0:
                    break
                
                if creditor['amount'] <= 0:
                    continue
                
                claim_amount = min(remaining, creditor['amount'])
                
                # إنشاء مطالبة
                PartnerClaim.objects.create(
                    batch=self,
                    from_partner=debtor['partner'],
                    to_partner=creditor['partner'],
                    amount=claim_amount
                )
                
                remaining -= claim_amount
                creditor['amount'] -= claim_amount
        
        return self.claims.all()
    
    def post(self):
        """ترحيل التسوية"""
        if self.status != 'open':
            raise ValidationError("يمكن ترحيل الدفعات المفتوحة فقط")
        
        from django.utils import timezone
        
        # تحديث الرصيد المرحّل لكل شريك
        for line in self.lines.all():
            line.project_partner.carry_forward += line.diff
            line.project_partner.save()
        
        self.status = 'posted'
        self.posted_at = timezone.now()
        self.save()
    
    def reverse(self):
        """عكس التسوية"""
        if self.status != 'posted':
            raise ValidationError("يمكن عكس الدفعات المرحّلة فقط")
        
        from django.utils import timezone
        
        # عكس الرصيد المرحّل
        for line in self.lines.all():
            line.project_partner.carry_forward -= line.diff
            line.project_partner.save()
        
        self.status = 'reversed'
        self.reversed_at = timezone.now()
        self.save()

class PartnerSettleLine(models.Model):
    """سطور التسوية لكل شريك"""
    batch = models.ForeignKey(PartnerSettleBatch, on_delete=models.CASCADE,
                             related_name='lines',
                             verbose_name="دفعة التسوية")
    partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE,
                               verbose_name="الشريك")
    project_partner = models.ForeignKey('partners.ProjectPartner', on_delete=models.CASCADE,
                                       verbose_name="محفظة الشريك")
    share_pct_at_cutoff = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="نسبة الحصة عند القطع %"
    )
    should_bear = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="ما يجب تحمله"
    )
    actually_paid = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="ما تم دفعه فعلاً"
    )
    diff = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الفرق"
    )
    
    class Meta:
        verbose_name = "سطر تسوية"
        verbose_name_plural = "سطور التسوية"
        ordering = ['batch', '-diff']
        unique_together = ['batch', 'partner']
        
    def __str__(self):
        status = "دائن" if self.diff > 0 else "مدين" if self.diff < 0 else "متوازن"
        return f"{self.partner.name} - {abs(self.diff)} ({status})"
    
    def get_status(self):
        """حالة الشريك في التسوية"""
        if self.diff > 0:
            return 'creditor'  # دائن (له فلوس)
        elif self.diff < 0:
            return 'debtor'    # مدين (عليه فلوس)
        else:
            return 'balanced'  # متوازن

class PartnerClaim(models.Model):
    """المطالبات بين الشركاء"""
    STATUS_CHOICES = [
        ('pending', 'معلقة'),
        ('settled', 'مسددة'),
        ('void', 'ملغاة'),
    ]
    
    batch = models.ForeignKey(PartnerSettleBatch, on_delete=models.CASCADE,
                             related_name='claims',
                             verbose_name="دفعة التسوية")
    from_partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE,
                                    related_name='claims_from',
                                    verbose_name="من الشريك (المدين)")
    to_partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE,
                                  related_name='claims_to',
                                  verbose_name="إلى الشريك (الدائن)")
    amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                            default='pending', verbose_name="الحالة")
    settled_voucher_id = models.IntegerField(null=True, blank=True,
                                            verbose_name="رقم سند التسديد")
    settled_date = models.DateField(null=True, blank=True,
                                   verbose_name="تاريخ التسديد")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "مطالبة"
        verbose_name_plural = "المطالبات"
        ordering = ['batch', '-amount']
        
    def __str__(self):
        return f"{self.from_partner.name} → {self.to_partner.name}: {self.amount}"
    
    def settle(self, voucher_id=None):
        """تسديد المطالبة"""
        from django.utils import timezone
        
        self.status = 'settled'
        self.settled_voucher_id = voucher_id
        self.settled_date = timezone.now().date()
        self.save()
    
    def void(self):
        """إلغاء المطالبة"""
        self.status = 'void'
        self.save()