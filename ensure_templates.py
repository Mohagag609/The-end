#!/usr/bin/env python
"""
التأكد من وجود جميع القوالب المطلوبة
"""

import os

# القوالب المطلوبة
required_templates = {
    'base.html': '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Musharaka Pro{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
</head>
<body class="bg-gray-50">
    {% block content %}{% endblock %}
</body>
</html>''',

    'error.html': '''{% extends 'base.html' %}
{% block title %}خطأ{% endblock %}
{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-md p-6 text-center">
        <i class="fas fa-exclamation-triangle text-6xl text-yellow-500 mb-4"></i>
        <h1 class="text-2xl font-bold text-gray-900 mb-2">عذراً، حدث خطأ</h1>
        <p class="text-gray-600 mb-4">{{ message|default:"الصفحة المطلوبة غير متاحة حالياً" }}</p>
        <a href="/" class="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
            العودة للرئيسية
        </a>
    </div>
</div>
{% endblock %}''',

    'partners/partners_list.html': '''{% extends 'base.html' %}
{% block title %}الشركاء{% endblock %}
{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-md p-6">
        <h1 class="text-2xl font-bold text-gray-900 mb-4">
            <i class="fas fa-users ml-2"></i>
            قائمة الشركاء
        </h1>
        <div class="mb-4">
            <a href="/project/{{ project.id }}/partners/add/" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                <i class="fas fa-plus ml-2"></i>
                إضافة شريك
            </a>
        </div>
        {% if partners %}
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الحصة</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الرصيد</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for partner in partners %}
                    <tr>
                        <td class="px-6 py-4">{{ partner.partner.name }}</td>
                        <td class="px-6 py-4">{{ partner.share_pct }}%</td>
                        <td class="px-6 py-4">{{ partner.balance|default:0 }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p class="text-gray-500 text-center py-8">لا يوجد شركاء حتى الآن</p>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    'expenses/expenses_list.html': '''{% extends 'base.html' %}
{% block title %}المصروفات{% endblock %}
{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-md p-6">
        <h1 class="text-2xl font-bold text-gray-900 mb-4">
            <i class="fas fa-money-bill-wave ml-2"></i>
            المصروفات
        </h1>
        <div class="mb-4">
            <a href="/project/{{ project.id }}/expenses/create/" class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                <i class="fas fa-plus ml-2"></i>
                إضافة مصروف
            </a>
        </div>
        {% if expenses %}
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">التاريخ</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الوصف</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">المبلغ</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for expense in expenses %}
                    <tr>
                        <td class="px-6 py-4">{{ expense.date }}</td>
                        <td class="px-6 py-4">{{ expense.description }}</td>
                        <td class="px-6 py-4">{{ expense.amount }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p class="text-gray-500 text-center py-8">لا توجد مصروفات حتى الآن</p>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    'projects/stages_list.html': '''{% extends 'base.html' %}
{% block title %}المراحل{% endblock %}
{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-md p-6">
        <h1 class="text-2xl font-bold text-gray-900 mb-4">
            <i class="fas fa-layer-group ml-2"></i>
            مراحل المشروع
        </h1>
        <div class="mb-4">
            <a href="/project/{{ project.id }}/stages/add/" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">
                <i class="fas fa-plus ml-2"></i>
                إضافة مرحلة
            </a>
        </div>
        {% if stages %}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {% for stage in stages %}
            <div class="border rounded-lg p-4">
                <h3 class="font-bold text-lg mb-2">{{ stage.name }}</h3>
                <p class="text-gray-600 text-sm mb-2">{{ stage.description|truncatechars:50 }}</p>
                <div class="flex justify-between text-sm">
                    <span>الميزانية: {{ stage.budget }}</span>
                    <span class="{% if stage.status == 'active' %}text-green-600{% else %}text-gray-600{% endif %}">
                        {{ stage.get_status_display|default:stage.status }}
                    </span>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-gray-500 text-center py-8">لا توجد مراحل حتى الآن</p>
        {% endif %}
    </div>
</div>
{% endblock %}'''
}

def ensure_templates():
    """التأكد من وجود جميع القوالب"""
    templates_dir = '/workspace/templates'
    
    for template_path, content in required_templates.items():
        full_path = os.path.join(templates_dir, template_path)
        
        # إنشاء المجلد إذا لم يكن موجوداً
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # إنشاء القالب إذا لم يكن موجوداً
        if not os.path.exists(full_path):
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Created: {template_path}")
        else:
            print(f"✓ Exists: {template_path}")

if __name__ == '__main__':
    print("🔍 التحقق من القوالب...")
    ensure_templates()
    print("✅ جميع القوالب موجودة!")