from app import db
from app.extensions import db
from datetime import datetime
from flask_login import UserMixin

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_added = db.Column(db.Date, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    category = db.Column(db.String(100))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(32), nullable=False, default="pc")
    barcode = db.Column(db.String(100), unique=True, nullable=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref='transactions')
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    price = db.Column(db.Float)
    season = db.Column(db.String(20))
    customer_id = db.Column(db.Integer)
    category = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password).decode('utf-8')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    contact = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.Date)
    profile_picture = db.Column(db.String(200), default='default_profile.png')
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def __repr__(self):
        return f"<Product {self.name}>"