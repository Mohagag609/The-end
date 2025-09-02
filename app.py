from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, Project, Partner, ProjectPartner, Supplier, Item, Warehouse, Stage, PurchaseInvoice, PurchaseInvoiceItem, StockMove, Expense, Voucher, Allocation, PartnerSettleBatch, PartnerSettleLine, PartnerClaim, WalletPriority
from datetime import datetime, date
from decimal import Decimal
import json
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.from_object(Config)
db.init_app(app)

# Helper Functions
def validate_shares(project_id):
    """التحقق من أن مجموع الحصص = 100%"""
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    total = sum(p.share_pct for p in partners)
    return abs(total - Decimal('100.00')) < Decimal('0.01')

def get_stage_total_cost(stage_id):
    """حساب إجمالي تكلفة المرحلة"""
    expenses = Expense.query.filter_by(stage_id=stage_id).all()
    stock_issues = StockMove.query.filter_by(stage_id=stage_id).filter(StockMove.qty_out > 0).all()
    
    total = sum(e.amount for e in expenses) + sum(s.amount for s in stock_issues)
    return Decimal(str(total))

def get_already_allocated(stage_id):
    """حساب ما تم توزيعه بالفعل على المرحلة"""
    allocations = Allocation.query.filter_by(stage_id=stage_id, posted=True).all()
    return sum(a.total_amount for a in allocations)

def calculate_delta(stage_id):
    """حساب Delta للتوزيع"""
    total = get_stage_total_cost(stage_id)
    allocated = get_already_allocated(stage_id)
    return total - allocated

def update_wallet_balance(project_partner_id, amount, operation='add'):
    """تحديث رصيد المحفظة"""
    pp = ProjectPartner.query.get(project_partner_id)
    if pp:
        if operation == 'add':
            pp.wallet_balance += Decimal(str(amount))
        elif operation == 'subtract':
            pp.wallet_balance -= Decimal(str(amount))
        db.session.commit()
        return True
    return False

def generate_ref_code(prefix='V'):
    """توليد كود مرجعي فريد"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}-{timestamp}"

# Routes
@app.route('/')
def index():
    """الصفحة الرئيسية - قائمة المشاريع"""
    projects = Project.query.all()
    for project in projects:
        project.partner_count = len(project.partners)
        project.stage_count = len(project.stages)
        # حساب الإنفاق الكلي
        project.total_spent = sum(e.amount for e in project.expenses)
    return render_template('index.html', projects=projects)

@app.route('/project/new', methods=['GET', 'POST'])
def new_project():
    """إنشاء مشروع جديد"""
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        
        # التحقق من عدم تكرار الكود
        if Project.query.filter_by(code=code).first():
            flash('كود المشروع موجود بالفعل', 'error')
            return redirect(url_for('new_project'))
        
        project = Project(
            code=code,
            name=name,
            base_currency='EGP',
            status='open'
        )
        db.session.add(project)
        db.session.commit()
        
        # إنشاء مخزن افتراضي
        warehouse = Warehouse(
            project_id=project.id,
            name='المخزن الرئيسي'
        )
        db.session.add(warehouse)
        db.session.commit()
        
        flash('تم إنشاء المشروع بنجاح', 'success')
        return redirect(url_for('project_dashboard', project_id=project.id))
    
    return render_template('project_new.html')

@app.route('/project/<int:project_id>')
def project_redirect(project_id):
    """إعادة توجيه إلى لوحة التحكم"""
    return redirect(url_for('project_dashboard', project_id=project_id))

@app.route('/project/<int:project_id>/dashboard')
def project_dashboard(project_id):
    """لوحة التحكم الرئيسية للمشروع"""
    project = Project.query.get_or_404(project_id)
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    stages = Stage.query.filter_by(project_id=project_id).all()
    
    # حساب مجموع الحصص
    total_shares = sum(p.share_pct for p in partners)
    shares_valid = abs(total_shares - Decimal('100.00')) < Decimal('0.01')
    
    # حساب تكاليف المراحل
    for stage in stages:
        stage.total_cost = get_stage_total_cost(stage.id)
        stage.allocated = get_already_allocated(stage.id)
        stage.delta = stage.total_cost - stage.allocated
    
    # إحصائيات للوحة التحكم
    stats = {
        'partners_count': len(partners),
        'stages_count': len(stages),
        'total_expenses': sum(e.amount for e in project.expenses),
        'total_wallets': sum(p.wallet_balance for p in partners)
    }
    
    # النشاطات الأخيرة
    recent_activities = []
    
    # جميع المشاريع للتبديل
    all_projects = Project.query.all()
    
    return render_template('dashboard.html', 
                         current_project=project,
                         all_projects=all_projects,
                         partners=partners,
                         stages=stages,
                         total_shares=total_shares,
                         shares_valid=shares_valid,
                         stats=stats,
                         recent_activities=recent_activities,
                         active_page='dashboard')

@app.route('/project/<int:project_id>/partners')
def project_partners(project_id):
    """صفحة الشركاء والمحافظ"""
    project = Project.query.get_or_404(project_id)
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    
    # حساب مجموع الحصص
    total_shares = sum(p.share_pct for p in partners)
    shares_valid = abs(total_shares - Decimal('100.00')) < Decimal('0.01')
    
    # حساب الإحصائيات
    total_deposits = Decimal('0')
    total_withdrawals = Decimal('0')
    total_balance = Decimal('0')
    
    for pp in partners:
        # حساب الإيداعات والسحوبات لكل شريك
        deposits = db.session.query(db.func.sum(Voucher.amount)).filter(
            Voucher.project_id == project_id,
            Voucher.party_id == pp.partner_id,
            Voucher.v_type == 'receipt'
        ).scalar() or Decimal('0')
        
        withdrawals = db.session.query(db.func.sum(Voucher.amount)).filter(
            Voucher.project_id == project_id,
            Voucher.party_id == pp.partner_id,
            Voucher.v_type == 'payment'
        ).scalar() or Decimal('0')
        
        pp.total_deposits = deposits
        pp.total_withdrawals = withdrawals
        pp.total_allocations = Decimal('0')  # يمكن حسابها لاحقاً
        
        total_deposits += deposits
        total_withdrawals += withdrawals
        total_balance += pp.wallet_balance
    
    # جميع المشاريع للتبديل
    all_projects = Project.query.all()
    
    return render_template('partners_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         partners=partners,
                         total_shares=total_shares,
                         shares_valid=shares_valid,
                         total_deposits=total_deposits,
                         total_withdrawals=total_withdrawals,
                         total_balance=total_balance,
                         active_page='partners')

@app.route('/project/<int:project_id>/add_partner', methods=['POST'])
def add_partner(project_id):
    """إضافة شريك للمشروع"""
    project = Project.query.get_or_404(project_id)
    
    partner_name = request.form.get('partner_name')
    share_pct = Decimal(request.form.get('share_pct', '0'))
    
    # البحث عن الشريك أو إنشاؤه
    partner = Partner.query.filter_by(name=partner_name).first()
    if not partner:
        partner = Partner(name=partner_name)
        db.session.add(partner)
        db.session.flush()
    
    # التحقق من عدم تكرار الشريك في المشروع
    existing = ProjectPartner.query.filter_by(
        project_id=project_id,
        partner_id=partner.id
    ).first()
    
    if existing:
        flash('الشريك موجود بالفعل في المشروع', 'error')
        return redirect(url_for('project_home', project_id=project_id))
    
    # إضافة الشريك للمشروع
    project_partner = ProjectPartner(
        project_id=project_id,
        partner_id=partner.id,
        share_pct=share_pct,
        wallet_balance=Decimal('0'),
        carry_forward_balance=Decimal('0')
    )
    db.session.add(project_partner)
    db.session.commit()
    
    # التحقق من مجموع الحصص
    if not validate_shares(project_id):
        flash('تحذير: مجموع الحصص لا يساوي 100%', 'warning')
    else:
        flash('تم إضافة الشريك بنجاح', 'success')
    
    return redirect(url_for('project_partners', project_id=project_id))

@app.route('/project/<int:project_id>/wallet/<int:partner_id>/deposit', methods=['POST'])
def wallet_deposit(project_id, partner_id):
    """إيداع في محفظة الشريك"""
    amount = Decimal(request.form.get('amount', '0'))
    notes = request.form.get('notes', '')
    
    pp = ProjectPartner.query.filter_by(
        project_id=project_id,
        partner_id=partner_id
    ).first_or_404()
    
    # تحديث رصيد المحفظة
    pp.wallet_balance += amount
    
    # إنشاء voucher
    voucher = Voucher(
        project_id=project_id,
        v_type='receipt',
        party_type='partner',
        party_id=partner_id,
        amount=amount,
        v_date=date.today(),
        ref_code=generate_ref_code('REC'),
        notes=notes
    )
    db.session.add(voucher)
    db.session.commit()
    
    flash(f'تم الإيداع بنجاح: {amount} جنيه', 'success')
    return redirect(url_for('project_partners', project_id=project_id))

@app.route('/project/<int:project_id>/wallet/<int:partner_id>/withdraw', methods=['POST'])
def wallet_withdraw(project_id, partner_id):
    """سحب من محفظة الشريك"""
    amount = Decimal(request.form.get('amount', '0'))
    notes = request.form.get('notes', '')
    
    pp = ProjectPartner.query.filter_by(
        project_id=project_id,
        partner_id=partner_id
    ).first_or_404()
    
    # التحقق من الرصيد
    wallet_priority = WalletPriority.query.filter_by(project_id=project_id).first()
    if not wallet_priority or not wallet_priority.allow_negative:
        if pp.wallet_balance < amount:
            flash('الرصيد غير كافي للسحب', 'error')
            return redirect(url_for('project_home', project_id=project_id))
    
    # تحديث رصيد المحفظة
    pp.wallet_balance -= amount
    
    # إنشاء voucher
    voucher = Voucher(
        project_id=project_id,
        v_type='payment',
        party_type='partner',
        party_id=partner_id,
        amount=amount,
        v_date=date.today(),
        ref_code=generate_ref_code('PAY'),
        notes=notes
    )
    db.session.add(voucher)
    db.session.commit()
    
    flash(f'تم السحب بنجاح: {amount} جنيه', 'success')
    return redirect(url_for('project_partners', project_id=project_id))

@app.route('/project/<int:project_id>/stage/new', methods=['POST'])
def new_stage(project_id):
    """إنشاء مرحلة جديدة"""
    project = Project.query.get_or_404(project_id)
    
    name = request.form.get('name')
    budget = Decimal(request.form.get('budget', '0'))
    
    stage = Stage(
        project_id=project_id,
        name=name,
        budget=budget,
        status='open'
    )
    db.session.add(stage)
    db.session.commit()
    
    flash('تم إنشاء المرحلة بنجاح', 'success')
    return redirect(url_for('project_stages', project_id=project_id))

@app.route('/project/<int:project_id>/expense/quick', methods=['POST'])
def quick_expense(project_id):
    """إضافة مصروف سريع"""
    stage_id = request.form.get('stage_id')
    amount = Decimal(request.form.get('amount', '0'))
    description = request.form.get('description')
    
    expense = Expense(
        project_id=project_id,
        stage_id=stage_id if stage_id else None,
        expense_date=date.today(),
        amount=amount,
        payee_type='other',
        description=description
    )
    db.session.add(expense)
    db.session.commit()
    
    flash('تم إضافة المصروف بنجاح', 'success')
    return redirect(url_for('project_expenses', project_id=project_id))

@app.route('/project/<int:project_id>/stage/<int:stage_id>/allocate', methods=['POST'])
def allocate_stage(project_id, stage_id):
    """توزيع تكلفة المرحلة على الشركاء"""
    stage = Stage.query.get_or_404(stage_id)
    delta = calculate_delta(stage_id)
    
    if delta <= 0:
        flash('لا يوجد مبلغ للتوزيع', 'info')
        return redirect(url_for('project_home', project_id=project_id))
    
    # التحقق من صحة الحصص
    if not validate_shares(project_id):
        flash('لا يمكن التوزيع - مجموع الحصص لا يساوي 100%', 'error')
        return redirect(url_for('project_home', project_id=project_id))
    
    rule = request.form.get('rule', 'by_share')
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    
    allocation_details = {}
    
    if rule == 'by_share':
        # توزيع حسب النسب
        for pp in partners:
            partner_amount = (delta * pp.share_pct / Decimal('100')).quantize(Decimal('0.01'))
            allocation_details[str(pp.partner_id)] = float(partner_amount)
            # خصم من المحفظة
            pp.wallet_balance -= partner_amount
    else:
        # توزيع مخصص (يحتاج واجهة إضافية)
        flash('التوزيع المخصص غير مفعل حالياً', 'warning')
        return redirect(url_for('project_home', project_id=project_id))
    
    # إنشاء سجل التوزيع
    allocation = Allocation(
        project_id=project_id,
        stage_id=stage_id,
        rule=rule,
        details_json=json.dumps(allocation_details),
        total_amount=delta,
        posted=True,
        alloc_date=date.today()
    )
    db.session.add(allocation)
    db.session.commit()
    
    flash(f'تم توزيع {delta} جنيه على الشركاء', 'success')
    return redirect(url_for('project_stages', project_id=project_id))

@app.route('/suppliers')
def suppliers():
    """قائمة الموردين"""
    suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/supplier/new', methods=['POST'])
def new_supplier():
    """إنشاء مورد جديد"""
    name = request.form.get('name')
    
    supplier = Supplier(name=name)
    db.session.add(supplier)
    db.session.commit()
    
    flash('تم إضافة المورد بنجاح', 'success')
    return redirect(url_for('suppliers'))

@app.route('/project/<int:project_id>/purchases')
def purchases(project_id):
    """قائمة المشتريات"""
    project = Project.query.get_or_404(project_id)
    invoices = PurchaseInvoice.query.filter_by(project_id=project_id).order_by(PurchaseInvoice.invoice_date.desc()).all()
    suppliers = Supplier.query.all()
    items = Item.query.all()
    warehouses = Warehouse.query.filter_by(project_id=project_id).all()
    all_projects = Project.query.all()
    
    return render_template('purchases_page.html', 
                         current_project=project,
                         all_projects=all_projects,
                         invoices=invoices,
                         suppliers=suppliers,
                         items=items,
                         warehouses=warehouses,
                         active_page='purchases')

@app.route('/project/<int:project_id>/purchase/new', methods=['POST'])
def new_purchase(project_id):
    """إنشاء فاتورة شراء"""
    supplier_id = request.form.get('supplier_id')
    warehouse_id = request.form.get('warehouse_id')
    invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
    
    # إنشاء الفاتورة
    invoice = PurchaseInvoice(
        project_id=project_id,
        supplier_id=supplier_id,
        invoice_date=invoice_date,
        total=Decimal('0'),
        status='posted'
    )
    db.session.add(invoice)
    db.session.flush()
    
    # إضافة الأصناف
    total = Decimal('0')
    item_ids = request.form.getlist('item_id[]')
    quantities = request.form.getlist('qty[]')
    costs = request.form.getlist('cost[]')
    
    for i in range(len(item_ids)):
        if item_ids[i]:
            qty = Decimal(quantities[i])
            cost = Decimal(costs[i])
            line_total = qty * cost
            
            # إضافة سطر الفاتورة
            invoice_item = PurchaseInvoiceItem(
                invoice_id=invoice.id,
                item_id=item_ids[i],
                qty=qty,
                unit_cost=cost,
                tax=Decimal('0')
            )
            db.session.add(invoice_item)
            
            # إنشاء حركة مخزن (دخول)
            stock_move = StockMove(
                project_id=project_id,
                warehouse_id=warehouse_id,
                item_id=item_ids[i],
                qty_in=qty,
                qty_out=Decimal('0'),
                unit_cost=cost,
                amount=line_total,
                ref_type='PI',
                ref_id=invoice.id,
                move_date=invoice_date
            )
            db.session.add(stock_move)
            
            # تحديث التكلفة القياسية للصنف
            item = Item.query.get(item_ids[i])
            if item:
                item.std_cost = cost
            
            total += line_total
    
    invoice.total = total
    db.session.commit()
    
    flash('تم إنشاء فاتورة الشراء بنجاح', 'success')
    return redirect(url_for('purchases', project_id=project_id))

@app.route('/project/<int:project_id>/stock/issue', methods=['POST'])
def stock_issue(project_id):
    """صرف مخزون لمرحلة"""
    warehouse_id = request.form.get('warehouse_id')
    item_id = request.form.get('item_id')
    stage_id = request.form.get('stage_id')
    qty = Decimal(request.form.get('qty', '0'))
    
    item = Item.query.get_or_404(item_id)
    amount = qty * item.std_cost
    
    # إنشاء حركة مخزن (خروج)
    stock_move = StockMove(
        project_id=project_id,
        warehouse_id=warehouse_id,
        item_id=item_id,
        stage_id=stage_id,
        qty_in=Decimal('0'),
        qty_out=qty,
        unit_cost=item.std_cost,
        amount=amount,
        ref_type='ISSUE',
        move_date=date.today()
    )
    db.session.add(stock_move)
    
    # إنشاء مصروف للمرحلة
    expense = Expense(
        project_id=project_id,
        stage_id=stage_id,
        expense_date=date.today(),
        amount=amount,
        payee_type='other',
        description=f'صرف مخزون: {item.name} ({qty} {item.uom})'
    )
    db.session.add(expense)
    db.session.commit()
    
    flash('تم صرف المخزون بنجاح', 'success')
    return redirect(url_for('purchases', project_id=project_id))

@app.route('/project/<int:project_id>/settlements')
def settlements(project_id):
    """قائمة التسويات"""
    project = Project.query.get_or_404(project_id)
    batches = PartnerSettleBatch.query.filter_by(project_id=project_id).order_by(PartnerSettleBatch.cutoff_date.desc()).all()
    all_projects = Project.query.all()
    
    return render_template('settlements_page.html', 
                         current_project=project,
                         all_projects=all_projects,
                         batches=batches,
                         active_page='settlements')

@app.route('/project/<int:project_id>/settlement/new', methods=['GET', 'POST'])
def new_settlement(project_id):
    """إنشاء تسوية جديدة"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        cutoff_date = datetime.strptime(request.form.get('cutoff_date'), '%Y-%m-%d').date()
        
        # حساب التكلفة الكلية حتى التاريخ
        expenses = Expense.query.filter(
            Expense.project_id == project_id,
            Expense.expense_date <= cutoff_date
        ).all()
        
        stock_issues = StockMove.query.filter(
            StockMove.project_id == project_id,
            StockMove.move_date <= cutoff_date,
            StockMove.qty_out > 0
        ).all()
        
        total_cost = sum(e.amount for e in expenses) + sum(s.amount for s in stock_issues)
        
        # إنشاء دفعة التسوية
        batch = PartnerSettleBatch(
            project_id=project_id,
            cutoff_date=cutoff_date,
            status='open',
            total_cost_until_cutoff=total_cost
        )
        db.session.add(batch)
        db.session.flush()
        
        # إنشاء سطور التسوية
        partners = ProjectPartner.query.filter_by(project_id=project_id).all()
        claims = []
        
        for pp in partners:
            # ما يجب أن يتحمله
            should_bear = (total_cost * pp.share_pct / Decimal('100')).quantize(Decimal('0.01'))
            
            # ما دفعه فعلاً
            deposits = Voucher.query.filter(
                Voucher.project_id == project_id,
                Voucher.party_id == pp.partner_id,
                Voucher.v_type == 'receipt',
                Voucher.v_date <= cutoff_date
            ).all()
            
            withdrawals = Voucher.query.filter(
                Voucher.project_id == project_id,
                Voucher.party_id == pp.partner_id,
                Voucher.v_type == 'payment',
                Voucher.v_date <= cutoff_date
            ).all()
            
            partner_expenses = Expense.query.filter(
                Expense.project_id == project_id,
                Expense.partner_id == pp.partner_id,
                Expense.expense_date <= cutoff_date
            ).all()
            
            actually_paid = (
                sum(d.amount for d in deposits) - 
                sum(w.amount for w in withdrawals) + 
                sum(e.amount for e in partner_expenses)
            )
            
            # الفرق مع الرصيد المرحل
            diff = actually_paid - should_bear + pp.carry_forward_balance
            
            # إنشاء سطر التسوية
            line = PartnerSettleLine(
                batch_id=batch.id,
                partner_id=pp.partner_id,
                project_partner_id=pp.id,
                share_pct_at_cutoff=pp.share_pct,
                should_bear_amount=should_bear,
                actually_paid_amount=actually_paid,
                diff_amount=diff
            )
            db.session.add(line)
            
            if diff != 0:
                claims.append((pp.partner_id, pp.partner.name, diff))
        
        # توليد المطالبات (Claims) - Greedy Algorithm
        creditors = [(p_id, name, amt) for p_id, name, amt in claims if amt > 0]
        debtors = [(p_id, name, -amt) for p_id, name, amt in claims if amt < 0]
        
        creditors.sort(key=lambda x: x[2], reverse=True)
        debtors.sort(key=lambda x: x[2], reverse=True)
        
        for debtor_id, debtor_name, debt_amount in debtors:
            remaining_debt = debt_amount
            
            for i, (creditor_id, creditor_name, credit_amount) in enumerate(creditors):
                if remaining_debt <= 0:
                    break
                
                if credit_amount > 0:
                    transfer = min(remaining_debt, credit_amount)
                    
                    # إنشاء مطالبة
                    claim = PartnerClaim(
                        batch_id=batch.id,
                        from_partner_id=debtor_id,
                        to_partner_id=creditor_id,
                        amount=transfer,
                        status='pending'
                    )
                    db.session.add(claim)
                    
                    remaining_debt -= transfer
                    creditors[i] = (creditor_id, creditor_name, credit_amount - transfer)
        
        db.session.commit()
        
        flash('تم إنشاء التسوية بنجاح', 'success')
        return redirect(url_for('settlement_preview', project_id=project_id, batch_id=batch.id))
    
    all_projects = Project.query.all()
    return render_template('settlement_new.html', 
                         current_project=project,
                         all_projects=all_projects,
                         active_page='settlements')

@app.route('/project/<int:project_id>/settlement/<int:batch_id>/preview')
def settlement_preview(project_id, batch_id):
    """معاينة التسوية"""
    project = Project.query.get_or_404(project_id)
    batch = PartnerSettleBatch.query.get_or_404(batch_id)
    lines = PartnerSettleLine.query.filter_by(batch_id=batch_id).all()
    claims = PartnerClaim.query.filter_by(batch_id=batch_id).all()
    all_projects = Project.query.all()
    
    return render_template('settlement_preview.html', 
                         current_project=project,
                         all_projects=all_projects,
                         project_id=project_id,
                         batch=batch, 
                         lines=lines, 
                         claims=claims,
                         active_page='settlements')

@app.route('/project/<int:project_id>/settlement/<int:batch_id>/post', methods=['POST'])
def settlement_post(project_id, batch_id):
    """ترحيل التسوية"""
    batch = PartnerSettleBatch.query.get_or_404(batch_id)
    
    if batch.status == 'posted':
        flash('التسوية مرحلة بالفعل', 'warning')
        return redirect(url_for('settlements', project_id=project_id))
    
    # تحديث الأرصدة المرحلة
    lines = PartnerSettleLine.query.filter_by(batch_id=batch_id).all()
    for line in lines:
        pp = ProjectPartner.query.get(line.project_partner_id)
        pp.carry_forward_balance += line.diff_amount
    
    batch.status = 'posted'
    batch.posted_at = datetime.now()
    db.session.commit()
    
    flash('تم ترحيل التسوية بنجاح', 'success')
    return redirect(url_for('settlements', project_id=project_id))

@app.route('/project/<int:project_id>/wallets')
def wallets_overview(project_id):
    """نظرة عامة على المحافظ"""
    project = Project.query.get_or_404(project_id)
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    
    # حساب الإحصائيات
    total_deposits = db.session.query(db.func.sum(Voucher.amount)).filter(
        Voucher.project_id == project_id,
        Voucher.v_type == 'receipt'
    ).scalar() or Decimal('0')
    
    total_withdrawals = db.session.query(db.func.sum(Voucher.amount)).filter(
        Voucher.project_id == project_id,
        Voucher.v_type == 'payment'
    ).scalar() or Decimal('0')
    
    allocations = Allocation.query.filter_by(project_id=project_id, posted=True).all()
    total_allocations = sum(a.total_amount for a in allocations)
    
    total_balance = sum(p.wallet_balance for p in partners)
    
    # تفاصيل كل شريك
    partner_details = []
    for pp in partners:
        deposits = db.session.query(db.func.sum(Voucher.amount)).filter(
            Voucher.project_id == project_id,
            Voucher.party_id == pp.partner_id,
            Voucher.v_type == 'receipt'
        ).scalar() or Decimal('0')
        
        withdrawals = db.session.query(db.func.sum(Voucher.amount)).filter(
            Voucher.project_id == project_id,
            Voucher.party_id == pp.partner_id,
            Voucher.v_type == 'payment'
        ).scalar() or Decimal('0')
        
        # حساب التوزيعات للشريك
        partner_allocations = Decimal('0')
        for allocation in allocations:
            details = json.loads(allocation.details_json)
            partner_allocations += Decimal(str(details.get(str(pp.partner_id), 0)))
        
        partner_details.append({
            'partner': pp.partner,
            'share_pct': pp.share_pct,
            'wallet_balance': pp.wallet_balance,
            'carry_forward': pp.carry_forward_balance,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'allocations': partner_allocations
        })
    
    return render_template('wallets_overview.html',
                         project=project,
                         wallet_count=len(partners),
                         total_deposits=total_deposits,
                         total_withdrawals=total_withdrawals,
                         total_allocations=total_allocations,
                         total_balance=total_balance,
                         partner_details=partner_details)

@app.route('/project/<int:project_id>/report/partner/<int:partner_id>')
def partner_statement(project_id, partner_id):
    """كشف حساب شريك"""
    project = Project.query.get_or_404(project_id)
    partner = Partner.query.get_or_404(partner_id)
    pp = ProjectPartner.query.filter_by(project_id=project_id, partner_id=partner_id).first_or_404()
    
    # جمع كل الحركات
    movements = []
    
    # الإيداعات والسحوبات
    vouchers = Voucher.query.filter_by(project_id=project_id, party_id=partner_id).order_by(Voucher.v_date).all()
    for v in vouchers:
        movements.append({
            'date': v.v_date,
            'type': 'إيداع' if v.v_type == 'receipt' else 'سحب',
            'description': v.notes or v.ref_code,
            'debit': v.amount if v.v_type == 'payment' else Decimal('0'),
            'credit': v.amount if v.v_type == 'receipt' else Decimal('0'),
            'ref': v.ref_code
        })
    
    # التوزيعات
    allocations = Allocation.query.filter_by(project_id=project_id, posted=True).all()
    for a in allocations:
        details = json.loads(a.details_json)
        amount = Decimal(str(details.get(str(partner_id), 0)))
        if amount > 0:
            movements.append({
                'date': a.alloc_date,
                'type': 'توزيع',
                'description': f'توزيع مرحلة {a.stage.name}',
                'debit': amount,
                'credit': Decimal('0'),
                'ref': f'ALLOC-{a.id}'
            })
    
    # ترتيب حسب التاريخ
    movements.sort(key=lambda x: x['date'])
    
    # حساب الرصيد المتحرك
    balance = pp.carry_forward_balance
    for m in movements:
        balance = balance + m['credit'] - m['debit']
        m['balance'] = balance
    
    return render_template('partner_statement.html',
                         project=project,
                         partner=partner,
                         project_partner=pp,
                         movements=movements,
                         final_balance=balance)

@app.route('/project/<int:project_id>/priority', methods=['GET', 'POST'])
def wallet_priority(project_id):
    """إعداد ترتيب الخصم"""
    project = Project.query.get_or_404(project_id)
    priority = WalletPriority.query.filter_by(project_id=project_id).first()
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    
    if request.method == 'POST':
        partner_order = request.form.getlist('partner_order[]')
        allow_negative = request.form.get('allow_negative') == 'on'
        credit_limit = request.form.get('credit_limit')
        
        if not priority:
            priority = WalletPriority(project_id=project_id)
            db.session.add(priority)
        
        priority.ordered_partner_ids = json.dumps([int(p) for p in partner_order])
        priority.allow_negative = allow_negative
        priority.credit_limit_per_partner = Decimal(credit_limit) if credit_limit else None
        
        db.session.commit()
        flash('تم حفظ إعدادات الخصم', 'success')
        return redirect(url_for('project_home', project_id=project_id))
    
    return render_template('wallet_priority.html',
                         project=project,
                         priority=priority,
                         partners=partners)

@app.route('/item/new', methods=['POST'])
def new_item():
    """إنشاء صنف جديد"""
    sku = request.form.get('sku')
    name = request.form.get('name')
    uom = request.form.get('uom', 'unit')
    std_cost = Decimal(request.form.get('std_cost', '0'))
    
    # التحقق من عدم تكرار SKU
    if Item.query.filter_by(sku=sku).first():
        return jsonify({'error': 'كود الصنف موجود بالفعل'}), 400
    
    item = Item(
        sku=sku,
        name=name,
        uom=uom,
        std_cost=std_cost
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'id': item.id,
        'sku': item.sku,
        'name': item.name,
        'uom': item.uom,
        'std_cost': float(item.std_cost)
    })

@app.route('/api/items')
def api_items():
    """API للحصول على قائمة الأصناف"""
    items = Item.query.all()
    return jsonify([{
        'id': i.id,
        'sku': i.sku,
        'name': i.name,
        'uom': i.uom,
        'std_cost': float(i.std_cost)
    } for i in items])

@app.route('/project/<int:project_id>/stages')
def project_stages(project_id):
    """صفحة المراحل"""
    project = Project.query.get_or_404(project_id)
    stages = Stage.query.filter_by(project_id=project_id).all()
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    
    # حساب مجموع الحصص للتحقق من إمكانية التوزيع
    total_shares = sum(p.share_pct for p in partners)
    shares_valid = abs(total_shares - Decimal('100.00')) < Decimal('0.01')
    
    # حساب تكاليف المراحل
    for stage in stages:
        stage.total_cost = get_stage_total_cost(stage.id)
        stage.allocated = get_already_allocated(stage.id)
        stage.delta = stage.total_cost - stage.allocated
    
    all_projects = Project.query.all()
    
    return render_template('stages_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         stages=stages,
                         shares_valid=shares_valid,
                         active_page='stages')

@app.route('/project/<int:project_id>/expenses')
def project_expenses(project_id):
    """صفحة المصروفات"""
    project = Project.query.get_or_404(project_id)
    expenses = Expense.query.filter_by(project_id=project_id).order_by(Expense.expense_date.desc()).all()
    stages = Stage.query.filter_by(project_id=project_id).all()
    all_projects = Project.query.all()
    
    return render_template('expenses_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         expenses=expenses,
                         stages=stages,
                         active_page='expenses')

@app.route('/project/<int:project_id>/allocations')
def project_allocations(project_id):
    """صفحة التوزيعات"""
    project = Project.query.get_or_404(project_id)
    allocations = Allocation.query.filter_by(project_id=project_id).order_by(Allocation.alloc_date.desc()).all()
    all_projects = Project.query.all()
    
    return render_template('allocations_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         allocations=allocations,
                         active_page='allocations')

@app.route('/project/<int:project_id>/reports')
def project_reports(project_id):
    """صفحة التقارير"""
    project = Project.query.get_or_404(project_id)
    all_projects = Project.query.all()
    
    return render_template('reports_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         active_page='reports')

@app.route('/project/<int:project_id>/settings')
def project_settings(project_id):
    """صفحة الإعدادات"""
    project = Project.query.get_or_404(project_id)
    priority = WalletPriority.query.filter_by(project_id=project_id).first()
    partners = ProjectPartner.query.filter_by(project_id=project_id).all()
    all_projects = Project.query.all()
    
    return render_template('settings_page.html',
                         current_project=project,
                         all_projects=all_projects,
                         priority=priority,
                         partners=partners,
                         active_page='settings')

# Initialize database on startup
with app.app_context():
    try:
        db.create_all()
        app.logger.info("Database tables initialized")
    except Exception as e:
        app.logger.warning(f"Database initialization warning: {e}")

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database initialized")
        except Exception as e:
            app.logger.warning(f"Could not initialize database: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)