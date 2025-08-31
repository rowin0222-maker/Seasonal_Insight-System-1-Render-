from app.models import Transaction
from datetime import datetime
from collections import defaultdict

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

def inventory_advice(product, current_stock):
    peak_season, seasonal = detect_peak_season(product.id)
    current_month = datetime.now().month

    upcoming_months = {
        "Summer Promo": [3, 4, 5],
        "Rainy Discount": [6, 7, 8],
        "Pre-Holiday Push": [9, 10, 11],
        "Holiday Season": [12, 1, 2]
    }

    if current_month in upcoming_months.get(peak_season, []):
        expected_demand = seasonal.get(peak_season, 0)
        if current_stock < expected_demand:
            return f"📦 Recommendation: Restock more for {peak_season} (Expected demand: {expected_demand})."
        else:
            return f"✅ Stock is sufficient for {peak_season}."
    else:
        return f"🛑 Off-season: Hold inventory. Avoid overstocking {product.name}."