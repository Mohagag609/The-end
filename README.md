# Musharaka Pro - نظام إدارة المشاريع التشاركية

نظام متكامل لإدارة المشاريع التشاركية بين عدة شركاء، مع إدارة المحافظ والتوزيعات والتسويات.

## المميزات الرئيسية

- ✅ إدارة مشاريع متعددة مع شركاء بنسب مختلفة
- ✅ نظام محافظ متكامل (إيداع/سحب/توزيعات)
- ✅ إدارة المراحل والمصروفات
- ✅ نظام المشتريات والمخزون
- ✅ التسويات الدورية بين الشركاء
- ✅ الخصم المتسلسل من المحافظ
- ✅ تقارير تفصيلية وكشوف حساب
- ✅ واجهة عربية RTL احترافية

## التقنيات المستخدمة

- **Backend**: Python 3.11+ / Flask
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **ORM**: SQLAlchemy
- **Frontend**: Jinja2 Templates + Tailwind CSS + HTMX
- **Deployment**: Render.com

## النشر على Render

### خطوات النشر السريع:

1. **Fork أو Clone المشروع على GitHub**

2. **إنشاء حساب على Render.com**

3. **إنشاء Web Service جديد:**
   - اختر "New Web Service"
   - اربط مع GitHub repository
   - استخدم الإعدادات التالية:
     - **Name**: musharaka-pro
     - **Environment**: Python
     - **Build Command**: `./build.sh`
     - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120`

4. **إضافة متغيرات البيئة:**
   ```
   DATABASE_URL=postgresql://the_end_user:igNRMZF47KsVBOZxMG5Y4av7QycN4Msw@dpg-d2r8ibmr433s73facjng-a/the_end
   SECRET_KEY=[generate-a-secure-key]
   FLASK_ENV=production
   ```

5. **Deploy!**

## البنية الأساسية

```
/workspace/
├── app.py              # التطبيق الرئيسي والمسارات
├── models.py           # نماذج قاعدة البيانات
├── config.py           # إعدادات التطبيق
├── build.sh            # سكريبت البناء لـ Render
├── requirements.txt    # المكتبات المطلوبة
├── templates/          # قوالب HTML
│   ├── base.html      # القالب الأساسي
│   ├── index.html     # الصفحة الرئيسية
│   ├── project_home.html
│   ├── purchases.html
│   ├── settlements.html
│   └── ...
└── static/            # الملفات الثابتة

```

## قاعدة البيانات

النظام يستخدم PostgreSQL في الإنتاج مع الجداول التالية:

- **Projects**: المشاريع
- **Partners**: الشركاء (مشترك)
- **ProjectPartners**: ربط الشركاء بالمشاريع مع النسب
- **Suppliers**: الموردون (مشترك)
- **Items**: الأصناف
- **Warehouses**: المخازن
- **Stages**: مراحل المشروع
- **PurchaseInvoices**: فواتير الشراء
- **StockMoves**: حركات المخزون
- **Expenses**: المصروفات
- **Vouchers**: إيصالات الإيداع/السحب
- **Allocations**: توزيعات التكاليف
- **PartnerSettleBatches**: دفعات التسوية
- **WalletPriority**: ترتيب الخصم من المحافظ

## قواعد العمل الأساسية

1. **الحصص**: مجموع حصص الشركاء في أي مشروع يجب أن يساوي 100%
2. **المحافظ**: لكل شريك محفظة في كل مشروع مع رصيد قابل للإيداع والسحب
3. **التوزيعات**: يتم توزيع تكاليف المراحل على الشركاء حسب نسبهم
4. **التسويات**: تحسب الفروقات بين ما دفعه كل شريك وما يجب أن يتحمله
5. **الخصم المتسلسل**: عند عدم كفاية رصيد محفظة، يتم الخصم من المحافظ الأخرى بالترتيب

## الأمان

- استخدام متغيرات البيئة للمعلومات الحساسة
- SQL Injection Protection عبر SQLAlchemy ORM
- CSRF Protection (يمكن تفعيله لاحقاً)
- Input Validation على جميع النماذج

## التطوير المحلي

```bash
# Clone the repository
git clone [your-repo-url]
cd musharaka-pro

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run the application
flask run
```

## الدعم

للمساعدة أو الإبلاغ عن مشاكل، يرجى فتح Issue على GitHub.

## الترخيص

هذا المشروع مفتوح المصدر ومتاح للاستخدام التجاري وغير التجاري.