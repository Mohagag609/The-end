#!/usr/bin/env python
"""
إصلاح جميع القوالب لإزالة dashboard namespace
"""

import os
import re

def fix_template(filepath):
    """إصلاح قالب واحد"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # استبدال dashboard:home بـ /
    content = re.sub(r"\{% url 'dashboard:home' %\}", "/", content)
    
    # استبدال dashboard:project_dashboard بـ /project/ID/
    content = re.sub(r"\{% url 'dashboard:project_dashboard' project\.id %\}", "/project/{{ project.id }}/", content)
    content = re.sub(r"\{% url 'dashboard:project_dashboard' (\w+)\.id %\}", r"/project/{{ \1.id }}/", content)
    
    # استبدال dashboard:kpis
    content = re.sub(r"\{% url 'dashboard:kpis' project\.id %\}", "/project/{{ project.id }}/kpis/", content)
    
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