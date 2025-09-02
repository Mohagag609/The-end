from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal
import json

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    base_currency = db.Column(db.String(10), default='EGP')
    status = db.Column(db.String(20), default='open')  # open/closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    partners = db.relationship('ProjectPartner', back_populates='project', cascade='all, delete-orphan')
    stages = db.relationship('Stage', back_populates='project', cascade='all, delete-orphan')
    warehouses = db.relationship('Warehouse', back_populates='project', cascade='all, delete-orphan')
    purchase_invoices = db.relationship('PurchaseInvoice', back_populates='project', cascade='all, delete-orphan')
    stock_moves = db.relationship('StockMove', back_populates='project', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='project', cascade='all, delete-orphan')
    vouchers = db.relationship('Voucher', back_populates='project', cascade='all, delete-orphan')
    allocations = db.relationship('Allocation', back_populates='project', cascade='all, delete-orphan')
    settle_batches = db.relationship('PartnerSettleBatch', back_populates='project', cascade='all, delete-orphan')
    wallet_priority = db.relationship('WalletPriority', back_populates='project', uselist=False, cascade='all, delete-orphan')

class Partner(db.Model):
    __tablename__ = 'partners'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_partners = db.relationship('ProjectPartner', back_populates='partner')
    vouchers = db.relationship('Voucher', back_populates='partner')
    expenses = db.relationship('Expense', back_populates='partner')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.code:
            # Generate unique code
            last_partner = Partner.query.order_by(Partner.id.desc()).first()
            if last_partner and last_partner.id:
                self.code = f"PTR{last_partner.id + 1:04d}"
            else:
                self.code = "PTR0001"

class ProjectPartner(db.Model):
    __tablename__ = 'project_partners'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=False)
    share_pct = db.Column(db.Numeric(5, 2), nullable=False)  # 0.00 to 100.00
    wallet_balance = db.Column(db.Numeric(14, 2), default=0)
    carry_forward_balance = db.Column(db.Numeric(14, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='partners')
    partner = db.relationship('Partner', back_populates='project_partners')
    settle_lines = db.relationship('PartnerSettleLine', back_populates='project_partner')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('project_id', 'partner_id'),)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(200), nullable=False)
    contact_info = db.Column(db.String(200))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_invoices = db.relationship('PurchaseInvoice', back_populates='supplier')
    expenses = db.relationship('Expense', back_populates='supplier')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.code:
            # Generate unique code
            last_supplier = Supplier.query.order_by(Supplier.id.desc()).first()
            if last_supplier:
                self.code = f"SUP{last_supplier.id + 1:04d}"
            else:
                self.code = "SUP0001"

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(50), default='قطعة')
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    std_cost = db.Column(db.Numeric(14, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_items = db.relationship('PurchaseInvoiceItem', back_populates='item')
    stock_moves = db.relationship('StockMove', back_populates='item')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.code:
            # Generate unique code
            last_item = Item.query.order_by(Item.id.desc()).first()
            if last_item:
                self.code = f"ITM{last_item.id + 1:04d}"
            else:
                self.code = "ITM0001"

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='warehouses')
    stock_moves = db.relationship('StockMove', back_populates='warehouse')

class Stage(db.Model):
    __tablename__ = 'stages'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    budget = db.Column(db.Numeric(14, 2), default=0)
    status = db.Column(db.String(20), default='open')  # open/closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='stages')
    stock_moves = db.relationship('StockMove', back_populates='stage')
    expenses = db.relationship('Expense', back_populates='stage')
    allocations = db.relationship('Allocation', back_populates='stage')

class PurchaseInvoice(db.Model):
    __tablename__ = 'purchase_invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=True)
    invoice_no = db.Column(db.String(100))
    invoice_date = db.Column(db.Date, nullable=False)
    total = db.Column(db.Numeric(14, 2), default=0)
    status = db.Column(db.String(20), default='posted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='purchase_invoices')
    supplier = db.relationship('Supplier', back_populates='purchase_invoices')
    stage = db.relationship('Stage', backref='purchase_invoices')
    items = db.relationship('PurchaseInvoiceItem', back_populates='invoice', cascade='all, delete-orphan')

class PurchaseInvoiceItem(db.Model):
    __tablename__ = 'purchase_invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('purchase_invoices.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    qty = db.Column(db.Numeric(14, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(14, 4), nullable=False)
    tax = db.Column(db.Numeric(14, 2), default=0)
    
    # Relationships
    invoice = db.relationship('PurchaseInvoice', back_populates='items')
    item = db.relationship('Item', back_populates='purchase_items')

class StockMove(db.Model):
    __tablename__ = 'stock_moves'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=True)
    qty_in = db.Column(db.Numeric(14, 3), default=0)
    qty_out = db.Column(db.Numeric(14, 3), default=0)
    unit_cost = db.Column(db.Numeric(14, 4), default=0)
    amount = db.Column(db.Numeric(14, 2), default=0)
    ref_type = db.Column(db.String(20))  # PI (Purchase Invoice) | ISSUE
    ref_id = db.Column(db.Integer)
    move_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='stock_moves')
    warehouse = db.relationship('Warehouse', back_populates='stock_moves')
    item = db.relationship('Item', back_populates='stock_moves')
    stage = db.relationship('Stage', back_populates='stock_moves')

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=True)
    expense_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    payee_type = db.Column(db.String(20))  # supplier | partner | other
    payee_id = db.Column(db.Integer, nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='expenses')
    stage = db.relationship('Stage', back_populates='expenses')
    supplier = db.relationship('Supplier', back_populates='expenses')
    partner = db.relationship('Partner', back_populates='expenses')

class Voucher(db.Model):
    __tablename__ = 'vouchers'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    v_type = db.Column(db.String(20), nullable=False)  # receipt | payment
    party_type = db.Column(db.String(20), default='partner')
    party_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    v_date = db.Column(db.Date, nullable=False)
    ref_code = db.Column(db.String(100), unique=True, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='vouchers')
    partner = db.relationship('Partner', back_populates='vouchers')

class Allocation(db.Model):
    __tablename__ = 'allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=False)
    rule = db.Column(db.String(20), nullable=False)  # by_share | custom
    details_json = db.Column(db.Text)  # JSON: {partner_id: amount}
    total_amount = db.Column(db.Numeric(14, 2), nullable=False)
    posted = db.Column(db.Boolean, default=False)
    alloc_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='allocations')
    stage = db.relationship('Stage', back_populates='allocations')
    
    @property
    def details(self):
        if self.details_json:
            return json.loads(self.details_json)
        return {}
    
    @details.setter
    def details(self, value):
        self.details_json = json.dumps(value)

class PartnerSettleBatch(db.Model):
    __tablename__ = 'partner_settle_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    cutoff_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='open')  # open | posted | reversed
    total_cost_until_cutoff = db.Column(db.Numeric(14, 2), default=0)
    notes = db.Column(db.Text)
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='settle_batches')
    lines = db.relationship('PartnerSettleLine', back_populates='batch', cascade='all, delete-orphan')
    claims = db.relationship('PartnerClaim', back_populates='batch', cascade='all, delete-orphan')

class PartnerSettleLine(db.Model):
    __tablename__ = 'partner_settle_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('partner_settle_batches.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=False)
    project_partner_id = db.Column(db.Integer, db.ForeignKey('project_partners.id'), nullable=False)
    share_pct_at_cutoff = db.Column(db.Numeric(5, 2), nullable=False)
    should_bear_amount = db.Column(db.Numeric(14, 2), nullable=False)
    actually_paid_amount = db.Column(db.Numeric(14, 2), nullable=False)
    diff_amount = db.Column(db.Numeric(14, 2), nullable=False)
    
    # Relationships
    batch = db.relationship('PartnerSettleBatch', back_populates='lines')
    project_partner = db.relationship('ProjectPartner', back_populates='settle_lines')

class PartnerClaim(db.Model):
    __tablename__ = 'partner_claims'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('partner_settle_batches.id'), nullable=False)
    from_partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=False)
    to_partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending | settled | void
    settled_voucher_id = db.Column(db.Integer, db.ForeignKey('vouchers.id'), nullable=True)
    settled_date = db.Column(db.Date)
    
    # Relationships
    batch = db.relationship('PartnerSettleBatch', back_populates='claims')
    from_partner = db.relationship('Partner', foreign_keys=[from_partner_id])
    to_partner = db.relationship('Partner', foreign_keys=[to_partner_id])

class WalletPriority(db.Model):
    __tablename__ = 'wallet_priorities'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    ordered_partner_ids = db.Column(db.Text)  # JSON array of partner IDs
    allow_negative = db.Column(db.Boolean, default=False)
    credit_limit_per_partner = db.Column(db.Numeric(14, 2), nullable=True)
    
    # Relationships
    project = db.relationship('Project', back_populates='wallet_priority')
    
    @property
    def partner_order(self):
        if self.ordered_partner_ids:
            return json.loads(self.ordered_partner_ids)
        return []
    
    @partner_order.setter
    def partner_order(self, value):
        self.ordered_partner_ids = json.dumps(value)