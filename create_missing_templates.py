#!/usr/bin/env python
"""Create missing template files with basic structure"""

import os

# Base template content
base_template = """{% extends 'base.html' %}
{% load humanize %}

{% block title %}{{ title|default:"الصفحة" }}{% endblock %}

{% block content %}
<div class="py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="text-2xl font-bold text-gray-900 mb-6">
            <i class="fas fa-file ml-2"></i>
            {{ title|default:"هذه الصفحة قيد الإنشاء" }}
        </h1>
        
        <div class="bg-white shadow rounded-lg p-6">
            <p class="text-gray-600">هذه الصفحة قيد التطوير وستكون متاحة قريباً.</p>
            
            {% if project %}
            <div class="mt-4">
                <a href="{% url 'dashboard:project_dashboard' project.id %}" 
                   class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    <i class="fas fa-arrow-right ml-2"></i>
                    العودة للوحة التحكم
                </a>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
"""

# Templates to create
templates = [
    # Partners
    'templates/partners/create_receipt.html',
    'templates/partners/create_payment.html',
    'templates/partners/wallets.html',
    'templates/partners/statement.html',
    
    # Projects
    'templates/projects/create_stage.html',
    'templates/projects/stage_detail.html',
    'templates/projects/warehouses.html',
    'templates/projects/create_warehouse.html',
    
    # Purchases
    'templates/purchases/list.html',
    'templates/purchases/create.html',
    'templates/purchases/invoice_detail.html',
    
    # Inventory
    'templates/inventory/list.html',
    'templates/inventory/items.html',
    'templates/inventory/issue.html',
    'templates/inventory/movements.html',
    
    # Expenses
    'templates/expenses/list.html',
    'templates/expenses/create.html',
    'templates/expenses/partials/quick_form.html',
    'templates/expenses/partials/expense_row.html',
    
    # Suppliers
    'templates/suppliers/list.html',
    'templates/suppliers/create.html',
    'templates/suppliers/detail.html',
    'templates/suppliers/statement.html',
    
    # Allocations
    'templates/allocations/allocate.html',
    'templates/allocations/history.html',
    
    # Settlements
    'templates/settlements/list.html',
    'templates/settlements/create.html',
    'templates/settlements/detail.html',
    
    # Reports
    'templates/reports/partners.html',
    'templates/reports/suppliers.html',
    'templates/reports/iron.html',
    
    # Dashboard
    'templates/dashboard/kpis.html',
    
    # Projects partials
    'templates/projects/partials/stages_list.html',
]

# Create templates
created = 0
skipped = 0

for template_path in templates:
    full_path = os.path.join('/workspace', template_path)
    
    # Check if file already exists
    if os.path.exists(full_path):
        print(f"✓ Already exists: {template_path}")
        skipped += 1
        continue
    
    # Create directory if needed
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Write template
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(base_template)
    
    print(f"✓ Created: {template_path}")
    created += 1

print(f"\n{'='*50}")
print(f"Summary: {created} templates created, {skipped} already existed")
print(f"Total templates: {len(templates)}")