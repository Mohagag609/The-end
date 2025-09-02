#!/usr/bin/env python
"""
Script to create sample data for testing
"""
import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musharaka_pro.settings')
django.setup()

from core.models import Currency, SystemSettings
from projects.models import Project, Stage, Warehouse
from partners.models import Partner, ProjectPartner, Voucher
from suppliers.models import Supplier
from inventory.models import ItemCategory, Item
from purchases.models import PurchaseInvoice, PurchaseItem
from expenses.models import Expense

def create_sample_data():
    print("Creating sample data...")
    
    # 1. Currency
    currency, _ = Currency.objects.get_or_create(
        code='EGP',
        defaults={
            'name': 'جنيه مصري',
            'symbol': 'ج.م',
            'is_default': True
        }
    )
    print("✓ Currency created")
    
    # 2. System Settings
    settings, _ = SystemSettings.objects.get_or_create(
        id=1,
        defaults={
            'allow_negative_wallet': False,
            'default_credit_limit': Decimal('10000.00')
        }
    )
    print("✓ System settings created")
    
    # 3. Create Project
    project = Project.objects.create(
        code='P001',
        name='مشروع برج النيل السكني',
        description='مشروع سكني متكامل يضم 120 وحدة سكنية',
        currency=currency,
        status='open'
    )
    print(f"✓ Project created: {project.name}")
    
    # 4. Create Warehouse
    warehouse = Warehouse.objects.create(
        project=project,
        name='المخزن الرئيسي',
        location='الموقع الرئيسي للمشروع'
    )
    print("✓ Warehouse created")
    
    # 5. Create Stages
    stages = [
        Stage.objects.create(
            project=project,
            name='الأساسات',
            budget=Decimal('500000.00'),
            status='active'
        ),
        Stage.objects.create(
            project=project,
            name='الهيكل الخرساني',
            budget=Decimal('1500000.00'),
            status='pending'
        ),
        Stage.objects.create(
            project=project,
            name='أعمال التشطيبات',
            budget=Decimal('800000.00'),
            status='pending'
        ),
    ]
    print(f"✓ {len(stages)} Stages created")
    
    # 6. Create Partners
    partners_data = [
        ('أحمد محمد', '40'),
        ('محمود السيد', '35'),
        ('فاطمة علي', '25'),
    ]
    
    partners = []
    for name, share in partners_data:
        partner = Partner.objects.create(
            name=name,
            phone='01000000000',
            email=f"{name.replace(' ', '').lower()}@example.com"
        )
        
        project_partner = ProjectPartner.objects.create(
            project=project,
            partner=partner,
            share_pct=Decimal(share)
        )
        partners.append(project_partner)
        
        # Create initial deposits
        voucher = Voucher.objects.create(
            project=project,
            type='receipt',
            partner=partner,
            project_partner=project_partner,
            amount=Decimal('100000.00'),
            date=datetime.now().date(),
            description='إيداع أولي'
        )
    
    print(f"✓ {len(partners)} Partners created with initial deposits")
    
    # 7. Create Suppliers
    suppliers = [
        Supplier.objects.create(
            name='شركة الحديد والصلب',
            phone='0223456789',
            address='القاهرة - مدينة نصر'
        ),
        Supplier.objects.create(
            name='مصنع الأسمنت الوطني',
            phone='0234567890',
            address='حلوان - القاهرة'
        ),
        Supplier.objects.create(
            name='شركة مواد البناء المتحدة',
            phone='0245678901',
            address='6 أكتوبر'
        ),
    ]
    print(f"✓ {len(suppliers)} Suppliers created")
    
    # 8. Create Item Categories and Items
    categories = {}
    for name, desc in [
        ('حديد', 'جميع أنواع الحديد'),
        ('أسمنت', 'جميع أنواع الأسمنت'),
        ('رمل وزلط', 'مواد الخرسانة'),
    ]:
        cat, _ = ItemCategory.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        categories[name.split()[0]] = cat  # Use first word as key
    
    items = []
    items_data = [
        ('IRON-12', 'حديد تسليح 12مم', 'حديد', 'TON', '15000.00'),
        ('IRON-16', 'حديد تسليح 16مم', 'حديد', 'TON', '15000.00'),
        ('CEM-PORT', 'أسمنت بورتلاندي', 'أسمنت', 'TON', '1200.00'),
        ('SAND-01', 'رمل ناعم', 'رمل', 'M3', '150.00'),
    ]
    
    for sku, name, cat_key, uom, cost in items_data:
        item, _ = Item.objects.get_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': categories[cat_key],
                'uom': uom,
                'std_cost': Decimal(cost)
            }
        )
        items.append(item)
    print(f"✓ {len(categories)} Categories and {len(items)} Items created")
    
    # 9. Create Purchase Invoice
    invoice = PurchaseInvoice.objects.create(
        project=project,
        supplier=suppliers[0],  # شركة الحديد والصلب
        invoice_no='INV-2024-001',
        date=datetime.now().date(),
        status='draft'
    )
    
    # Add items to invoice
    PurchaseItem.objects.create(
        invoice=invoice,
        item=items[0],  # حديد 12مم
        qty=Decimal('10.000'),
        unit_cost=Decimal('15500.0000'),
        tax_rate=Decimal('14.00')
    )
    
    PurchaseItem.objects.create(
        invoice=invoice,
        item=items[1],  # حديد 16مم
        qty=Decimal('5.000'),
        unit_cost=Decimal('15500.0000'),
        tax_rate=Decimal('14.00')
    )
    
    invoice.calculate_totals()
    invoice.post()  # Post to create stock movements
    print("✓ Purchase invoice created and posted")
    
    # 10. Create Expenses
    expenses = [
        Expense.objects.create(
            project=project,
            stage=stages[0],  # الأساسات
            date=datetime.now().date(),
            amount=Decimal('25000.00'),
            category='labor',
            payee_type='other',
            description='أجور عمال الحفر'
        ),
        Expense.objects.create(
            project=project,
            stage=stages[0],
            date=datetime.now().date() - timedelta(days=1),
            amount=Decimal('15000.00'),
            category='transport',
            payee_type='other',
            description='نقل معدات الحفر'
        ),
        Expense.objects.create(
            project=project,
            stage=stages[0],
            date=datetime.now().date() - timedelta(days=2),
            amount=Decimal('8000.00'),
            category='maintenance',
            payee_type='other',
            description='صيانة معدات'
        ),
    ]
    print(f"✓ {len(expenses)} Expenses created")
    
    print("\n" + "="*50)
    print("Sample data created successfully!")
    print("="*50)
    print(f"\nProject: {project.name} ({project.code})")
    print(f"Partners: {len(partners)} partners with total shares = 100%")
    print(f"Stages: {len(stages)} stages")
    print(f"Total initial deposits: 300,000 EGP")
    print(f"Total expenses so far: 48,000 EGP")
    print("\nYou can now login and explore the system!")
    print("URL: http://localhost:8000")
    print("Admin: http://localhost:8000/admin")
    print("Username: admin")
    print("Password: admin123")

if __name__ == '__main__':
    try:
        # Check if project already exists
        if Project.objects.filter(code='P001').exists():
            print("Sample data already exists. Skipping...")
        else:
            create_sample_data()
    except Exception as e:
        print(f"Error creating sample data: {e}")
        sys.exit(1)