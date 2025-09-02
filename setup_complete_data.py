#!/usr/bin/env python
"""
إعداد بيانات تجريبية كاملة للنظام
"""

import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musharaka_pro.settings')
django.setup()

from django.db import transaction
from core.models import Currency, SystemSettings
from projects.models import Project, Stage, Warehouse
from partners.models import Partner, ProjectPartner, Voucher, WalletPriority
from suppliers.models import Supplier
from inventory.models import ItemCategory, Item, StockMove
from purchases.models import PurchaseInvoice, PurchaseItem
from expenses.models import Expense

def setup_data():
    """إعداد البيانات التجريبية"""
    
    print("🚀 بدء إعداد البيانات...")
    
    with transaction.atomic():
        # 1. العملة والإعدادات
        print("💰 إعداد العملة...")
        currency, _ = Currency.objects.get_or_create(
            code='EGP',
            defaults={
                'name': 'جنيه مصري',
                'symbol': 'ج.م',
                'is_default': True
            }
        )
        
        system_settings, _ = SystemSettings.objects.get_or_create(
            id=1,
            defaults={
                'company_name': 'شركة المشاركة للاستثمار العقاري',
                'default_currency': currency
            }
        )
        
        # 2. المشروع
        print("🏗️ إنشاء المشروع...")
        project, created = Project.objects.get_or_create(
            code='P001',
            defaults={
                'name': 'برج النيل السكني',
                'description': 'مشروع سكني فاخر على كورنيش النيل',
                'currency': currency,
                'status': 'active'
            }
        )
        
        # 3. المخازن
        print("📦 إنشاء المخازن...")
        main_warehouse, _ = Warehouse.objects.get_or_create(
            project=project,
            name='المخزن الرئيسي',
            defaults={'location': 'الموقع الرئيسي'}
        )
        
        site_warehouse, _ = Warehouse.objects.get_or_create(
            project=project,
            name='مخزن الموقع',
            defaults={'location': 'موقع البناء'}
        )
        
        # 4. المراحل
        print("📊 إنشاء المراحل...")
        stages_data = [
            ('الأساسات', Decimal('500000'), 'أعمال الحفر والأساسات الخرسانية'),
            ('الهيكل الخرساني', Decimal('1500000'), 'البناء الخرساني للأدوار'),
            ('التشطيبات', Decimal('1000000'), 'أعمال التشطيب والدهانات'),
            ('الأعمال الكهربائية', Decimal('300000'), 'التمديدات والتركيبات الكهربائية'),
            ('السباكة والصرف', Decimal('200000'), 'أعمال السباكة والصرف الصحي'),
        ]
        
        stages = []
        for name, budget, desc in stages_data:
            stage, _ = Stage.objects.get_or_create(
                project=project,
                name=name,
                defaults={
                    'budget': budget,
                    'description': desc,
                    'status': 'active'
                }
            )
            stages.append(stage)
        
        # 5. الشركاء
        print("👥 إنشاء الشركاء...")
        partners_data = [
            ('أحمد محمد علي', '01012345678', Decimal('40')),
            ('محمود السيد أحمد', '01023456789', Decimal('35')),
            ('فاطمة علي حسن', '01034567890', Decimal('25')),
        ]
        
        project_partners = []
        for name, phone, share in partners_data:
            partner, _ = Partner.objects.get_or_create(
                name=name,
                defaults={'phone': phone}
            )
            
            pp, _ = ProjectPartner.objects.get_or_create(
                project=project,
                partner=partner,
                defaults={
                    'share_pct': share,
                    'credit_limit': Decimal('50000')
                }
            )
            project_partners.append(pp)
        
        # تعيين أولوية المحافظ للمشروع
        priority_order = [pp.id for pp in project_partners]
        WalletPriority.objects.get_or_create(
            project=project,
            defaults={
                'ordered_partner_ids': priority_order,
                'allow_negative': False,
                'credit_limit_per_partner': Decimal('50000')
            }
        )
        
        # 6. إيداعات الشركاء
        print("💵 إضافة إيداعات الشركاء...")
        for pp in project_partners:
            # إيداع أولي
            Voucher.objects.get_or_create(
                project=project,
                partner=pp.partner,
                type='receipt',
                date=datetime.now().date() - timedelta(days=30),
                defaults={
                    'project_partner': pp,
                    'amount': Decimal('200000'),
                    'description': 'إيداع أولي',
                    'ref_no': f'REC-{pp.partner.id:04d}'
                }
            )
            
            # إيداع ثاني
            Voucher.objects.get_or_create(
                project=project,
                partner=pp.partner,
                type='receipt',
                date=datetime.now().date() - timedelta(days=15),
                defaults={
                    'project_partner': pp,
                    'amount': Decimal('100000'),
                    'description': 'إيداع إضافي',
                    'ref_no': f'REC-{pp.partner.id:04d}-2'
                }
            )
        
        # 7. الموردين
        print("🚚 إنشاء الموردين...")
        suppliers_data = [
            ('شركة الحديد المتحدة', '0223456789'),
            ('مؤسسة الأسمنت العربي', '0234567890'),
            ('شركة المقاولات الحديثة', '0245678901'),
            ('محلات الكهرباء المتقدمة', '0256789012'),
        ]
        
        suppliers = []
        for name, phone in suppliers_data:
            supplier, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    'phone': phone
                }
            )
            suppliers.append(supplier)
        
        # 8. فئات وأصناف المخزون
        print("📋 إنشاء الأصناف...")
        
        # فئات الأصناف
        cat_steel, _ = ItemCategory.objects.get_or_create(name='حديد التسليح')
        cat_cement, _ = ItemCategory.objects.get_or_create(name='أسمنت')
        cat_sand, _ = ItemCategory.objects.get_or_create(name='رمل وزلط')
        cat_blocks, _ = ItemCategory.objects.get_or_create(name='طوب وبلوك')
        cat_electrical, _ = ItemCategory.objects.get_or_create(name='كهربائيات')
        
        # الأصناف
        items_data = [
            ('حديد تسليح 12مم', 'STL-12', cat_steel, 'ton', Decimal('15000')),
            ('حديد تسليح 16مم', 'STL-16', cat_steel, 'ton', Decimal('15000')),
            ('أسمنت بورتلاند', 'CEM-01', cat_cement, 'ton', Decimal('1200')),
            ('رمل ناعم', 'SND-01', cat_sand, 'm3', Decimal('150')),
            ('زلط', 'GRV-01', cat_sand, 'm3', Decimal('200')),
            ('طوب أحمر', 'BRK-01', cat_blocks, 'piece', Decimal('1.5')),
            ('كابلات كهرباء', 'ELC-01', cat_electrical, 'm', Decimal('50')),
        ]
        
        items = []
        for name, sku, category, uom, cost in items_data:
            item, _ = Item.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'category': category,
                    'uom': uom,
                    'std_cost': cost
                }
            )
            items.append(item)
        
        # 9. فواتير الشراء
        print("📄 إنشاء فواتير الشراء...")
        
        # فاتورة حديد
        invoice1, _ = PurchaseInvoice.objects.get_or_create(
            project=project,
            supplier=suppliers[0],
            invoice_no='INV-2024-001',
            defaults={
                'date': datetime.now().date() - timedelta(days=20),
                'status': 'posted'
            }
        )
        
        if invoice1:
            # بنود الفاتورة
            PurchaseItem.objects.get_or_create(
                invoice=invoice1,
                item=items[0],  # حديد 12مم
                defaults={
                    'qty': Decimal('10'),
                    'unit_cost': Decimal('15000'),
                    'tax_rate': Decimal('14')
                }
            )
            
            PurchaseItem.objects.get_or_create(
                invoice=invoice1,
                item=items[1],  # حديد 16مم
                defaults={
                    'qty': Decimal('5'),
                    'unit_cost': Decimal('15000'),
                    'tax_rate': Decimal('14')
                }
            )
            
            invoice1.calculate_totals()
            
            # ترحيل الفاتورة لإضافة المخزون
            if invoice1.status == 'draft':
                invoice1.post()
        
        # فاتورة أسمنت
        invoice2, _ = PurchaseInvoice.objects.get_or_create(
            project=project,
            supplier=suppliers[1],
            invoice_no='INV-2024-002',
            defaults={
                'date': datetime.now().date() - timedelta(days=15),
                'status': 'posted'
            }
        )
        
        if invoice2:
            PurchaseItem.objects.get_or_create(
                invoice=invoice2,
                item=items[2],  # أسمنت
                defaults={
                    'qty': Decimal('50'),
                    'unit_cost': Decimal('1200'),
                    'tax_rate': Decimal('14')
                }
            )
            
            invoice2.calculate_totals()
            
            if invoice2.status == 'draft':
                invoice2.post()
        
        # 10. المصروفات
        print("💸 إضافة المصروفات...")
        
        expenses_data = [
            (stages[0], 'labor', Decimal('50000'), 'أجور عمال الحفر', 'contractor'),
            (stages[0], 'equipment', Decimal('30000'), 'إيجار معدات حفر', 'other'),
            (stages[1], 'labor', Decimal('80000'), 'أجور عمال البناء', 'contractor'),
            (stages[1], 'materials', Decimal('25000'), 'مواد بناء متنوعة', 'supplier'),
            (stages[2], 'materials', Decimal('45000'), 'دهانات ومواد تشطيب', 'supplier'),
            (None, 'admin', Decimal('15000'), 'مصاريف إدارية', 'other'),
            (None, 'utilities', Decimal('5000'), 'كهرباء ومياه', 'other'),
        ]
        
        for stage, category, amount, desc, payee_type in expenses_data:
            Expense.objects.get_or_create(
                project=project,
                description=desc,
                amount=amount,
                defaults={
                    'stage': stage,
                    'category': category,
                    'date': datetime.now().date() - timedelta(days=10),
                    'payee_type': payee_type,
                    'payee_name': 'مقاول' if payee_type == 'contractor' else 'مورد'
                }
            )
        

        
        print("✅ تم إعداد جميع البيانات بنجاح!")
        
        # عرض ملخص
        print("\n📊 ملخص البيانات:")
        print(f"  • المشروع: {project.name}")
        print(f"  • المراحل: {Stage.objects.filter(project=project).count()}")
        print(f"  • الشركاء: {ProjectPartner.objects.filter(project=project).count()}")
        print(f"  • الموردين: {Supplier.objects.count()}")
        print(f"  • الأصناف: {Item.objects.count()}")
        print(f"  • الفواتير: {PurchaseInvoice.objects.filter(project=project).count()}")
        print(f"  • المصروفات: {Expense.objects.filter(project=project).count()}")
        print(f"  • حركات المخزون: {StockMove.objects.filter(project=project).count()}")
        
        # حساب الأرصدة
        total_deposits = Voucher.objects.filter(
            project=project, type='receipt'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_expenses = Expense.objects.filter(
            project=project
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        print(f"\n💰 الوضع المالي:")
        print(f"  • إجمالي الإيداعات: {total_deposits:,.0f} ج.م")
        print(f"  • إجمالي المصروفات: {total_expenses:,.0f} ج.م")
        print(f"  • الرصيد المتاح: {total_deposits - total_expenses:,.0f} ج.م")
        
        return project

if __name__ == '__main__':
    try:
        from django.db.models import Sum
        project = setup_data()
        print(f"\n🎉 النظام جاهز للاستخدام!")
        print(f"🔗 URL: http://localhost:8000/project/{project.id}/")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()