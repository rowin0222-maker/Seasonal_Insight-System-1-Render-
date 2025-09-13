from flask import render_template, request, flash
from app.models import Product
from .utils import inventory_advice
from app.advice import advice_bp


@advice_bp.route('/inventory_advice', methods=['GET', 'POST'])
def inventory_advice_view():
    if request.method == "POST":
        product_name = request.form["product"]
        stock = int(request.form["current_stock"])

        if not product_name or not stock:
            flash("Product name and stock are required", "danger")
            return render_template("inventory_advice.html")
        
        try:
            stock = int(stock)
        except ValueError:
            flash("Stock must be a number", "danger")
            return render_template("inventory_advice.html")
        
        product = Product.query.filter_by(name=product_name).first()
        if not product:
            flash("Product not found", "danger")
            return render_template("inventory_advice.html")
        
        advice = inventory_advice(product, stock)
        return render_template("inventory_advice.html", product=product_name, advice=advice)

    return render_template("inventory_advice.html")