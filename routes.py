from flask_login import login_user
from flask_login import login_required, current_user
from flask_login import current_user, login_required
from app.extensions import db, bcrypt
from flask import Blueprint, redirect, url_for, render_template, flash, request, session, abort, current_app, send_file, make_response, jsonify
from flask_dance.contrib.google import make_google_blueprint, google
from app.advice import advice_bp
from app.advice.forecast import generate_forecast
from app.advice.inventory_advice import inventory_advice
from app.advice.season import detect_peak_season
from werkzeug.utils import secure_filename
from sqlalchemy import extract, func
from flask import current_app
from prophet import Prophet
from app.models import Product, Transaction
from app.models import User
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from collections import defaultdict
from flask_bcrypt import Bcrypt
from .forecast import generate_forecast
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
from flask import send_file
from PIL import Image
import os
import re
import json
import random
import numpy as np
import uuid
import sqlite3
import pandas as pd
import requests

main = Blueprint('main', __name__)

@main.route('/')
def root():
    return redirect(url_for('main.login'))

@main.route('/index')
def index():
    product = Product.query.first()
    return render_template('index.html', product=product)

@main.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@main.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.login'))

@main.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@advice_bp.route('/some_page')
def some_page():
    return "Advice page"
@main.route('/barcode_scanner')
def barcode_scanner():
    return render_template('scanner.html')

@main.route("/verify_front", methods=["POST"])
def verify_front():
    data = request.get_json()
    front_code = data.get("front_code")
    
    if not front_code:
        return jsonify({"ok": False, "msg": "No front code detected"})
    
    # For now we just echo back. You could validate against DB here.
    return jsonify({"ok": True, "front": front_code})


@main.route("/verify_barcode", methods=["POST"])
def verify_barcode():
    data = request.get_json()
    barcode = data.get("barcode")

    product = productsDB.get(barcode)
    if product:
        return jsonify({"found": True, **product})
    return jsonify({"found": False})

inventory = []
    
bcrypt = Bcrypt()

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        user = User.query.filter_by(username=username).first()


        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash("Login successful!", "success")


            response = make_response(redirect(url_for('main.index')))
            response.set_cookie('username', '', expires=0)
            response.set_cookie('password', '', expires=0)
            return response

        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('main.login'))

    return render_template('login.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        contact = request.form['contact']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('main.signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!")
            return redirect(url_for('main.signup'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw, email=email, contact=contact)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created! You may now log in.", "success")


        response = make_response(redirect(url_for('main.login')))
        response.set_cookie('username', username, max_age=60*5)
        response.set_cookie('password', password, max_age=60*5)
        return response
    
    return render_template('signup.html')

@main.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'POST':

        transaction_id = request.form.get('transaction_id')
        product_name = request.form.get('product_name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        season = request.form.get('season')


        product = Product.query.filter_by(name=product_name).first()
        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for('main.transactions'))



        new_transaction = Transaction(
            transaction_id=transaction_id,
            product=product,
            quantity=quantity,
            price=product.price,
            season=season,
            date=datetime.utcnow(),
            user_id=current_user.id
        )

        db.session.add(new_transaction)
        db.session.commit()


        return redirect(url_for('main.transactions'))


    results = (
        db.session.query(Transaction, Product) \
        .filter(Transaction.user_id == current_user.id) \
        .join(Product, Transaction.product_id == Product.id) \
        .order_by(Transaction.date.desc()) \
        .all()
    )


    transactions = []
    for t, p in results:
        t.product = p
        transactions.append(t)

    return render_template("transactions.html", transactions=transactions)

@main.route('/forecast_summary', methods=['GET', 'POST'])
def forecast_summary():

    products = Product.query.all()
    transactions = Transaction.query.all()

    summary_ready = bool(transactions)
    low_stock_products = Product.query.filter(Product.stock < 10).all() if summary_ready else []

    # Initialize summary variables
    monthly_labels, monthly_values = [], []
    yearly_labels, yearly_values = [], []
    total_sales = gross_profit = total_orders = 0
    sales_trend_labels, sales_trend_values = [], []
    category_labels, category_values = [], []

    # Forecast-specific variables
    chart_ready = False
    labels, values, table_data = [], [], []
    product_name = ''
    forecast_unit = ''
    how_many = 0
    current_stock = 0

    # === SALES SUMMARY SECTION ===
    if summary_ready:
        monthly_summary = defaultdict(float)
        yearly_summary = defaultdict(float)

        for tx in transactions:
            if tx.date:
                month_key = tx.date.strftime('%Y-%m')
                year_key = tx.date.strftime('%Y')
                total = tx.quantity * tx.price
                monthly_summary[month_key] += total
                yearly_summary[year_key] += total

        monthly_data = sorted(monthly_summary.items())
        yearly_data = sorted(yearly_summary.items())

        monthly_labels = [m for m, _ in monthly_data]
        monthly_values = [round(v, 2) for _, v in monthly_data]
        yearly_labels = [y for y, _ in yearly_data]
        yearly_values = [round(v, 2) for _, v in yearly_data]

        total_sales = round(sum(monthly_values), 2)
        gross_profit = round(total_sales * 0.3, 2)
        total_orders = len(set(tx.customer_id for tx in transactions if tx.customer_id))

        sales_trend_labels = monthly_labels
        sales_trend_values = monthly_values

        # Category summary
        category_summary = defaultdict(float)
        for tx in transactions:
            product = Product.query.get(tx.product_id)
            if product and product.category:
                category_summary[product.category] += tx.quantity * tx.price

        category_labels = list(category_summary.keys())
        category_values = [round(v, 2) for v in category_summary.values()]

    # === FORECAST SECTION ===
    if request.method == 'POST':
        try:
            product_name = request.form.get('product', '').strip()
            forecast_unit = request.form.get('forecast_unit')
            how_many = int(request.form.get('how_many', 0) or 0)
            current_stock = int(request.form.get('current_stock', 0) or 0)
            quick_range = request.form.get('quick_range')

            # Quick range override
            if quick_range:
                quick_parts = quick_range.split('_')
                if len(quick_parts) == 2 and quick_parts[0].isdigit():
                    how_many = int(quick_parts[0])
                    forecast_unit = quick_parts[1]
                else:
                    flash("Invalid quick range selection.", "warning")
                    return redirect(url_for('main.forecast_summary'))

            # Fetch product
            product = Product.query.filter(
                func.lower(func.trim(Product.name)) == product_name.lower()
            ).first()

            if not product:
                flash("Product not found.", "danger")
                return redirect(url_for('main.forecast_summary'))

            # Forecast
            labels, values, table_data = generate_forecast(
                product, forecast_unit, how_many, current_stock
            )

            if not labels:
                flash("Not enough transaction data to forecast. At least 2 are needed.", "info")
            else:
                chart_ready = True

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash(f"Forecasting error: {e}", "danger")
            return redirect(url_for('main.forecast_summary'))
        
    transactions_data = []
    for t in transactions:
        transactions_data.append({
            "date": t.date.strftime("%Y-%m-%d") if t.date else None,
            "product": Product.query.get(t.product_id).name if t.product_id else None,
            "quantity": t.quantity,
            "season": getattr(t, "season", None)
        })

    return render_template("forecast_summary.html",
                           products=products,
                           chart_ready=chart_ready,
                           labels=labels,
                           values=values,
                           table_data=table_data,
                           product=product_name,
                           forecast_unit=forecast_unit,
                           how_many=how_many,
                           current_stock=current_stock,

                           summary_ready=summary_ready,
                           monthly_labels=monthly_labels,
                           monthly_values=monthly_values,
                           yearly_labels=yearly_labels,
                           yearly_values=yearly_values,
                           total_sales=total_sales,
                           gross_profit=gross_profit,
                           total_orders=total_orders,
                           sales_trend_labels=sales_trend_labels,
                           sales_trend_values=sales_trend_values,
                           category_labels=category_labels,
                           category_values=category_values,
                           low_stock_products=low_stock_products,
                           transactions_data=transactions_data,
                           zip=zip)

@main.route('/export_transactions')
def export_transactions():
    transactions = Transaction.query.all()

    if not transactions:
        flash("No transactions to export.", "warning")
        return redirect(url_for('main.transactions'))


    data = []
    for tx in transactions:
        data.append({
            'Transaction ID': tx.id,
            'Product': tx.product.name if tx.product else 'N/A',
            'Quantity': tx.quantity,
            'Price': tx.price,
            'Total': tx.quantity * tx.price,
            'Season': tx.season,
            'Date': tx.date.strftime('%Y-%m-%d') if tx.date else ''
        })

    df = pd.DataFrame(data)


    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')

    output.seek(0)

    return send_file(output,
                    as_attachment=True,
                    download_name='transactions.xlsx',
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@main.route('/export_transactions_csv')
def export_transactions_csv():
    transactions = Transaction.query.all()

    if not transactions:
        flash("No transactions to export.", "warning")
        return redirect(url_for('main.transactions'))

    data = []
    for tx in transactions:
        data.append({
            'Transaction ID': tx.id,
            'Product': tx.product.name if tx.product else 'N/A',
            'Quantity': tx.quantity,
            'Price': tx.price,
            'Total': tx.quantity * tx.price,
            'Season': tx.season,
            'Date': tx.date.strftime('%Y-%m-%d') if tx.date else ''
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    output.write(df.to_csv(index=False).encode('utf-8'))
    output.seek(0)

    return send_file(output,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name='transactions.csv')

@main.route('/export_transactions_pdf')
def export_transactions_pdf():
    transactions = Transaction.query.all()

    if not transactions:
        flash("No transactions to export.", "warning")
        return redirect(url_for('main.transactions'))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Transaction Report", ln=True, align='C')

    pdf.cell(30, 10, "ID", 1)
    pdf.cell(40, 10, "Product", 1)
    pdf.cell(20, 10, "Qty", 1)
    pdf.cell(30, 10, "Price", 1)
    pdf.cell(30, 10, "Total", 1)
    pdf.cell(40, 10, "Date", 1)
    pdf.ln()

    for tx in transactions:
        pdf.cell(30, 10, str(tx.id), 1)
        pdf.cell(40, 10, tx.product.name if tx.product else 'N/A', 1)
        pdf.cell(20, 10, str(tx.quantity), 1)
        pdf.cell(30, 10, f"{tx.price:.2f}", 1)
        pdf.cell(30, 10, f"{tx.quantity * tx.price:.2f}", 1)
        pdf.cell(40, 10, tx.date.strftime('%Y-%m-%d') if tx.date else '', 1)
        pdf.ln()

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    output = BytesIO(pdf_bytes)

    return send_file(output,
                    mimetype='/application/pdf',
                    as_attachment=True,
                    download_name='transactions.pdf')

@main.route('/add', methods=['GET', 'POST'])
@login_required
def add_transactions():
    if request.method == 'POST':
        # Get form fields
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        quantity_str = request.form.get('quantity')
        price_str = request.form.get('price')
        product_name = request.form.get('product_name')
        season = request.form.get('season', 'Unknown')

        # 🔵 PROCESS SECTION

    # ✅ Product Name Validation
        if product_name:
            product_name = product_name.strip()
        else:
            product_name = ''

        if not product_name:
            flash("Please enter a product name.", "danger")
            return redirect(url_for('main.add_transactions'))

    #💰 Price Validation
        try:
            price = float(price_str)
        except (ValueError, TypeError):
            flash('Invalid price format.', "danger")
            return redirect(url_for('main.add_transactions'))

        product = Product.query.filter_by(name=product_name).first()
        if not product:
            product = Product(name=product_name, date_added=datetime.utcnow(), stock=0, price=price, barcode=None, unit="pc")
            db.session.add(product)
            db.session.commit()


    #⏳ Quantity Validation
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                flash("Quantity must be a positive integer.", "danger")
                return redirect(url_for('main.add_transactions'))
        except (ValueError, TypeError):
            flash('Invalid quantity format.', "danger")
            return redirect(url_for('main.add_transactions'))
        
    #🕒 Timestamp Validation
        try:
            date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Invalid date format.', "danger")
            return redirect(url_for('main.add_transactions'))
        
        season_from_date = detect_peak_season(product_name)


        seasonal_event = request.form.get('season', 'Unknown')
        season = seasonal_event if seasonal_event != 'Other' else season_from_date

        # Check date range
        if not (datetime(2010, 1, 1) <= date <= datetime.now()):
            flash('Transaction date is out of range.', "danger")
            return redirect(url_for('main.add_transactions'))

        # Check for duplicate product
        existing = Transaction.query.filter_by(product_id=product.id, date=date).first()
        if existing:
            flash('Duplicate transaction already exists.', "danger")
            return redirect(url_for('main.add_transactions'))

        #🟢 OUTPUT: Save transaction
        new_tx = Transaction(
            transaction_id=str(uuid.uuid4())[:8],
            product_id=product.id,
            quantity=quantity,
            price=price,
            season=seasonal_event or season,
            date=date,
            category=product.category,
            user_id=current_user.id
        )
        db.session.add(new_tx)
        db.session.commit()

        # Clear forecast cache
        session.pop('forecast_dates', None)

        # Forecasting logic
        stmt = select(Transaction.date, Transaction.quantity).where(Transaction.user_id == current_user.id)
        result = db.session.execute(stmt)
        forecast_data = pd.DataFrame(result.fetchall(), columns=["ds", "y"])

        forecast_data['ds'] = pd.to_datetime(forecast_data['ds'])
        forecast_data.dropna(inplace=True)
        forecast_data = forecast_data[
            forecast_data['y'].apply(lambda x: pd.notnull(x) and np.isfinite(x))
        ]
        forecast_data = forecast_data[forecast_data['y'] >= 0]

        if len(forecast_data) < 2:
            flash("Not enough clean data to generate forecast.", "warning")
        else:
            model = Prophet()
            model.fit(forecast_data)
            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)
            forecast_output = forecast[['ds', 'yhat']].tail(10).to_dict(orient='records')
            flash('Forecast updated!', "success")

        return redirect(url_for('main.transactions'))

    # GET: Show form
    products = Product.query.all()
    return render_template('add_transactions.html', products=products)

@main.route('/edit_transactions/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transactions(id):
    transaction = Transaction.query.get_or_404(id)

    # 🚨 Security: make sure user can only edit their own
    if transaction.user_id != current_user.id:
        flash("You are not allowed to edit this transaction.", "danger")
        return redirect(url_for('main.transactions'))

    if request.method == 'POST':

        product_name = request.form['product_name']
        product = Product.query.filter_by(name=product_name).first()
        if not product:
            flash('Product not found.')
            return redirect(request.url)
        transaction.product_id = product.id

        transaction.quantity = int(request.form['quantity'])
        transaction.season = request.form['season']
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        db.session.commit()
        return redirect(url_for('main.transactions'))
    return render_template('edit_transactions.html', transaction=transaction)

@main.route('/delete_transactions/<int:id>', methods=['GET'])
def delete_transactions(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('main.transactions'))

@main.route('/inspect_transaction/<int:id>')
def inspect_transaction(id):
    try:
        transaction = Transaction.query.get_or_404(id)
        if transaction is None:
            raise ValueError("Transaction not found.")
        return render_template('inspect_transaction.html', transaction=transaction)
    except Exception as e:

        flash("🕵️‍♂️ Whoops! We couldn't locate that transaction. Maybe it went on vacation?", "warning")
        return render_template('error_transaction_not_found.html', error_message=str(e)), 404

@main.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for('main.login'))
    
    user_info = resp.json()
    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, username=name, password="oauth")
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in successfully with Google!", "success")
    return redirect(url_for("main.index"))

@main.route('/add_from_forecast', methods=['POST'])
def add_transactions_from_forecast():
    forecast_json = request.form.get('forecast_dates')
    try:
        forecast_data = json.loads(forecast_json)
        session['forecast_dates'] = forecast_data
    except Exception as e:
        flash("Error parsing forecast data.", "danger")
        return redirect(url_for('main.forecast'))
    
    return redirect(url_for('main.add_transactions'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@main.route('/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.profile'))
    
    file = request.files['profile_picture']

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.profile'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)


        upload_folder = os.path.join(current_app.root_path, 'static/uploads')
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        try:
            img = Image.open(file_path)
            img = img.convert("RGB")
            img = img.resize((600, 600), Image.Resampling.LANCZOS)
            img.save(file_path)
        except Exception as e:
            flash(f'Image processing failed: {str(e)}', 'danger')
            return redirect(url_for('main.profile'))


        current_user.profile_picture = filename
        db.session.commit()

        flash('Profile picture uploaded and resized to 2x2', 'success')
    else:
        flash('Unsupported file type.', 'danger')

    return redirect(url_for('main.profile'))



def detect_peak_season(product_id):
    txs = Transaction.query.filter_by(product_id=product_id).all()
    seasonal_sales = defaultdict(int)

    for tx in txs:
        month = tx.date.month
        if 3 <= month <= 5:
            season = "Summer Promo"
        elif 6 <= month <= 8:
            season = "Rainy Discount"
        elif 9 <= month <= 11:
            season = "Pre-Holiday Push"
        else:
            season = "Holiday Season"
        seasonal_sales[season] += tx.quantity

    if not seasonal_sales:
        return "No Sales Data", {}
    
    peak_season = max(seasonal_sales, key=seasonal_sales.get)
    return peak_season, seasonal_sales
    
# ---- ROUTE ----

@main.route('/product_insight', methods=['GET', 'POST'])
def product_insight():
    products = Product.query.all()

    if request.method == 'POST':
        product_name = request.form.get('product')  
        stock_str = request.form.get('current_stock')

        if not product_name or not stock_str:
            flash("Please provide both product and current stock.", "warning")
            return render_template('product_insight.html', products=products)
        
        try:
            stock = int(stock_str)
        except ValueError:
            flash("Stock must be a valid number.", "danger")
            return render_template('product_insight.html', products=products)
        
        product = Product.query.filter_by(name=product_name).first()
        if not product:
            flash("Product not found.", "danger")
            return render_template('product_insight.html', products=products)
        
        
        peak_season, season_data = detect_peak_season(product.id)
        advice = inventory_advice(product, stock)


        top_products = [("Product A", 120), ("Product B", 90)]
        slow_products = [("Product C", 5), ("Product D", 3)]

        forecast_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
        forecast_values = [15, 18, 20, 22]

        promotions = ["Product A", "Product B"]
        low_stock_alert = f"{product.name} is low on stock!" if stock < 10 else None

        return render_template(
            'product_insight.html',
            product=product,
            peak_season=peak_season,
            seasonal_data=season_data,
            top_products=top_products,
            slow_products=slow_products,
            forecast_ready=True,
            forecast_labels=json.dumps(forecast_labels),
            forecast_values=json.dumps(forecast_values),
            forecast_unit='weekly',
            recommended_promotions=promotions,
            advice=advice,
            current_stock=stock,
            products=products,
            low_stock_alert=low_stock_alert)
    

    return render_template('product_insight.html', products=products)