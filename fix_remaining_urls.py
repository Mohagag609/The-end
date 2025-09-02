#!/usr/bin/env python
"""
إصلاح باقي الروابط في القوالب
"""

import os
import re

def fix_template(filepath):
    """إصلاح قالب واحد"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # إصلاح روابط projects
    content = re.sub(r"\{% url 'projects:stages' project\.id %\}", "/project/{{ project.id }}/stages/", content)
    
    # إصلاح روابط expenses
    content = re.sub(r"\{% url 'expenses:create' project\.id %\}", "/project/{{ project.id }}/expenses/create/", content)
    content = re.sub(r"\{% url 'expenses:list' project\.id %\}", "/project/{{ project.id }}/expenses/", content)
    
    # إصلاح روابط partners
    content = re.sub(r"\{% url 'partners:create_receipt' project\.id %\}", "/project/{{ project.id }}/partners/voucher/receipt/", content)
    content = re.sub(r"\{% url 'partners:create_payment' project\.id %\}", "/project/{{ project.id }}/partners/voucher/payment/", content)
    content = re.sub(r"\{% url 'partners:wallets' project\.id %\}", "/project/{{ project.id }}/partners/wallets/", content)
    content = re.sub(r"\{% url 'partners:list' project\.id %\}", "/project/{{ project.id }}/partners/", content)
    content = re.sub(r"\{% url 'partners:add' project\.id %\}", "/project/{{ project.id }}/partners/add/", content)
    content = re.sub(r"\{% url 'partners:detail' project\.id (\w+)\.id %\}", r"/project/{{ project.id }}/partners/{{ \1.id }}/", content)
    content = re.sub(r"\{% url 'partners:wallet_detail' project\.id (\w+)\.id %\}", r"/project/{{ project.id }}/partners/wallet/{{ \1.id }}/", content)
    content = re.sub(r"\{% url 'partners:vouchers' project\.id %\}", "/project/{{ project.id }}/partners/vouchers/", content)
    
    # إصلاح روابط purchases
    content = re.sub(r"\{% url 'purchases:create' project\.id %\}", "/project/{{ project.id }}/purchases/create/", content)
    content = re.sub(r"\{% url 'purchases:list' project\.id %\}", "/project/{{ project.id }}/purchases/", content)
    
    # إصلاح روابط inventory
    content = re.sub(r"\{% url 'inventory:issue' project\.id %\}", "/project/{{ project.id }}/inventory/issue/", content)
    content = re.sub(r"\{% url 'inventory:items' project\.id %\}", "/project/{{ project.id }}/inventory/items/", content)
    content = re.sub(r"\{% url 'inventory:add_item' project\.id %\}", "/project/{{ project.id }}/inventory/items/add/", content)
    content = re.sub(r"\{% url 'inventory:movements' project\.id %\}", "/project/{{ project.id }}/inventory/movements/", content)
    content = re.sub(r"\{% url 'inventory:item_detail' project\.id (\w+)\.id %\}", r"/project/{{ project.id }}/inventory/items/{{ \1.id }}/", content)
    content = re.sub(r"\{% url 'inventory:receive' project\.id %\}", "/project/{{ project.id }}/inventory/receive/", content)
    content = re.sub(r"\{% url 'inventory:list' project\.id %\}", "/project/{{ project.id }}/inventory/movements/", content)
    
    # إصلاح روابط reports
    content = re.sub(r"\{% url 'reports:index' project\.id %\}", "/project/{{ project.id }}/reports/", content)
    content = re.sub(r"\{% url 'reports:stages' %\}", "/project/{{ project.id }}/reports/stages/", content)
    
    # إصلاح روابط settlements
    content = re.sub(r"\{% url 'settlements:list' project\.id %\}", "/project/{{ project.id }}/settlements/", content)
    
    # إصلاح روابط suppliers
    content = re.sub(r"\{% url 'suppliers:list' %\}", "/suppliers/", content)
    
    # إصلاح روابط allocations
    content = re.sub(r"\{% url 'allocations:list' project\.id %\}", "/project/{{ project.id }}/allocations/", content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """إصلاح جميع القوالب"""
    templates_dir = '/workspace/templates'
    fixed_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if fix_template(filepath):
                    fixed_count += 1
                    print(f"✅ Fixed: {filepath}")
    
    print(f"\n✨ تم إصلاح {fixed_count} ملف")

if __name__ == '__main__':
    main()