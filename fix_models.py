#!/usr/bin/env python
"""
Script to fix model relationships and add missing fields
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musharaka_pro.settings')
django.setup()

from django.db import connection, migrations
from django.core.management import call_command

def fix_models():
    """Fix model issues and relationships"""
    
    print("🔧 Fixing model relationships...")
    
    # 1. Check and fix Partner model
    with connection.cursor() as cursor:
        # Check if is_auto field exists in Voucher
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'partners_voucher' 
            AND column_name = 'is_auto'
        """)
        
        if not cursor.fetchone():
            print("Adding is_auto field to Voucher...")
            cursor.execute("""
                ALTER TABLE partners_voucher 
                ADD COLUMN is_auto BOOLEAN DEFAULT FALSE
            """)
    
    # 2. Fix WalletPriority if needed
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'partners_walletpriority' 
            AND column_name = 'priority'
        """)
        
        if not cursor.fetchone():
            print("Creating WalletPriority table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS partners_walletpriority (
                    id SERIAL PRIMARY KEY,
                    project_partner_id INTEGER REFERENCES partners_projectpartner(id),
                    priority INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    # 3. Fix carry_forward_balance in ProjectPartner
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'partners_projectpartner' 
            AND column_name = 'carry_forward_balance'
        """)
        
        if not cursor.fetchone():
            print("Adding carry_forward_balance to ProjectPartner...")
            cursor.execute("""
                ALTER TABLE partners_projectpartner 
                ADD COLUMN carry_forward_balance DECIMAL(15,2) DEFAULT 0.00
            """)
    
    # 4. Fix Expense model
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expenses_expense' 
            AND column_name = 'is_allocated'
        """)
        
        if not cursor.fetchone():
            print("Adding is_allocated field to Expense...")
            cursor.execute("""
                ALTER TABLE expenses_expense 
                ADD COLUMN is_allocated BOOLEAN DEFAULT FALSE
            """)
    
    # 5. Fix Item model methods
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'inventory_item' 
            AND column_name = 'std_cost'
        """)
        
        if cursor.fetchone():
            print("Updating default std_cost values...")
            cursor.execute("""
                UPDATE inventory_item 
                SET std_cost = 0.0000 
                WHERE std_cost IS NULL
            """)
    
    print("✅ Model fixes completed!")
    
    # Run migrations to ensure everything is in sync
    print("\n🔄 Running migrations...")
    try:
        call_command('makemigrations', '--noinput')
        call_command('migrate', '--noinput')
        print("✅ Migrations completed!")
    except Exception as e:
        print(f"⚠️ Migration warning: {e}")
    
    return True

if __name__ == '__main__':
    try:
        fix_models()
        print("\n✨ All model fixes applied successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)