# app/utils/advice.py

def inventory_advice(product, stock):
    """
    Generate simple inventory advice based on stock quantity.
    """
    if stock <= 0:
        return f"⚠️ Stock for {product.name} is depleted. Restock immediately!"
    elif stock < 10:
        return f"🔻 Stock for {product.name} is running low. Consider restocking soon."
    elif stock > 100:
        return f"🔺 You have a high stock level for {product.name}. Monitor sales to avoid overstocking."
    else:
        return f"✅ Stock level for {product.name} is healthy."