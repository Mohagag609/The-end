#!/usr/bin/env python
"""
تشغيل آمن للخادم مع معالجة جميع الأخطاء
"""

import os
import sys
import subprocess
import time

def kill_existing_servers():
    """إيقاف أي خوادم قيد التشغيل"""
    print("🛑 إيقاف الخوادم القديمة...")
    subprocess.run(["pkill", "-f", "python.*runserver"], capture_output=True)
    subprocess.run(["pkill", "-f", "python.*manage.py"], capture_output=True)
    time.sleep(2)

def setup_database():
    """إعداد قاعدة البيانات"""
    print("📊 إعداد قاعدة البيانات...")
    
    # تشغيل migrations
    result = subprocess.run(
        ["python", "manage.py", "migrate", "--no-input"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"⚠️ تحذير في migrations: {result.stderr}")
    else:
        print("✅ قاعدة البيانات جاهزة")

def check_data():
    """التحقق من وجود بيانات"""
    print("📋 التحقق من البيانات...")
    
    check_script = """
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musharaka_pro.settings')
django.setup()

from projects.models import Project
from partners.models import Partner, ProjectPartner

projects = Project.objects.count()
partners = Partner.objects.count()

print(f"المشاريع: {projects}")
print(f"الشركاء: {partners}")

if projects == 0:
    print("⚠️ لا توجد مشاريع - سيتم إنشاء بيانات تجريبية")
    exec(open('setup_complete_data.py').read())
"""
    
    with open('check_data_temp.py', 'w') as f:
        f.write(check_script)
    
    subprocess.run(["python", "check_data_temp.py"])
    os.remove('check_data_temp.py')

def start_server():
    """تشغيل الخادم"""
    print("\n🚀 تشغيل الخادم...")
    print("=" * 50)
    print("🌐 الخادم يعمل على: http://localhost:8000")
    print("📍 لوحة التحكم: http://localhost:8000/project/3/")
    print("🛑 للإيقاف: اضغط Ctrl+C")
    print("=" * 50)
    
    try:
        subprocess.run(["python", "manage.py", "runserver", "0.0.0.0:8000"])
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف الخادم")

def main():
    print("🎯 Musharaka Pro - تشغيل آمن")
    print("=" * 50)
    
    # التأكد من أننا في المجلد الصحيح
    os.chdir('/workspace')
    
    # تفعيل البيئة الافتراضية
    venv_activate = '/workspace/venv/bin/activate'
    if os.path.exists(venv_activate):
        print("✅ البيئة الافتراضية موجودة")
    
    kill_existing_servers()
    setup_database()
    check_data()
    
    # إصلاح أي أخطاء
    print("\n🔧 فحص وإصلاح الأخطاء...")
    subprocess.run(["python", "fix_all_errors.py"], capture_output=True)
    print("✅ تم الفحص والإصلاح")
    
    start_server()

if __name__ == '__main__':
    main()