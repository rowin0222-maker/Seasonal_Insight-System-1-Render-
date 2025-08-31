from collections import defaultdict
from app.models import Transaction

def detect_peak_season(product_identifier):
    """
    Detects the peak season for a product based on sales data or date provided.

    Args:
        product_identifier (int or str): Can be either product_id (int) or product_name (str).
        date (datetime, optional): Used if passing product_name to determine season manually.

    Returns:
        str: Peak season name.
    """

    if isinstance(product_identifier, str) and date:
        month = date.month
        name = product_identifier.lower()

        if "mountain dew" in name:
            return "Holiday Party Demand" if month in [12, 1] else "Summer Promo" if month in [2, 3, 4] else "Regular Sales"
        elif "water" in name:
            return "Hot Season Restock" if month in [3, 4, 5] else "Back-to-School" if month in [6, 7, 8] else "Regular Supply"
        elif "sprite" in name:
            return "Holiday Refreshments" if month in [11, 12, 1] else "Summer Promo" if month in [4, 5, 6] else "Regular Demand"
        elif "zesto" in name:
            return "Peak Juice Season" if month in [3, 4, 5] else "School Canteen Demand" if month in [6, 7, 8] else "Regular Sales"
        elif "corned beef" in name:
            return "Holiday and New Year Stock" if month in [12, 1, 2] else "Back-to-School" if month in [6, 7, 8] else "Pantry Refill Season"
        return "Standard Season"

    month_sales = defaultdict(int)

    product_id = product_identifier
    transactions = Transaction.query.filter_by(product_id=product_id).all()

    if not transactions:
        return "No Data"
    
    month_sales = defaultdict(int)
    for t in transactions:
        if t.date:
            month_sales[t.date.month] += t.quantity

    top_month = max(month_sales, key=month_sales.get)
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    return month_names[top_month]