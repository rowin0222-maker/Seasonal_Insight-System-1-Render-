from datetime import datetime
from app.models import Transaction
from sqlalchemy import extract
from collections import defaultdict

def determine_season(product_name: str, date: datetime) -> str:
    product_name = product_name.strip().lower()
    month = date.month

    if "mountain" in product_name and "dew" in product_name:
        if month in [12, 1]:
            return "Holiday Party Demand"
        elif month in [2, 3, 4]:
            return "Summer Promo"
        else:
            return "Regular Sales"
        
    elif "water" in product_name and "bottle" in product_name:
        if month in [3, 4, 5]:
            return "Hot Season Restock"
        elif month in [6, 7, 8]:
            return "Back-to-School"
        else:
            return "Regular Supply"
        
    elif "sprite" in product_name:
        if month in [11, 12, 1]:
            return "Holiday Refreshments"
        elif month in [4, 5, 6]:
            return "Summer Promo"
        else:
            return "Regular Demand"
        
    elif "zesto" in product_name:
        if month in [3, 4, 5]:
            return "Peak Juice Season"
        elif month in [6, 7, 8]:
            return "School Canteen Demand"
        else:
            return "Regular Sales"

    elif "corned beef" in product_name:
        if month in [12, 1, 2]:
            return "Holiday and New Year Stock"
        elif month in [6, 7, 8]:
            return "Back-to-School"
        elif month in [3, 4, 5]:
            return "Pantry Refill Season"
        
    return "Standard Season"

def detect_peak_season(product_id):
    month_sales = defaultdict(int)

    transactions = Transaction.query.filter_by(product_id=product_id).all()

    for t in transactions:
        if t.date:
            month = t.date.month
            month_sales[month] += t.quantity

    if not month_sales:
        return "No Data", {}
    
    sorted_sales = dict(sorted(month_sales.items(), key=lambda x: x[1], reverse=True))
    top_month = max(sorted_sales, key=sorted_sales.get)
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    return month_names[top_month], {month_names[k]: v for k, v in sorted_sales.items()}