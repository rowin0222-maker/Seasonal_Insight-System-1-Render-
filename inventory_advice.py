from app.models import Transaction
from app.advice.forecast import generate_forecast
from app.advice.season import detect_peak_season

def inventory_advice(product, current_stock):
    """
    Provides inventory advice based on stock levels, peak season, and forecasted demand.

    Args:
        product (Product): Product object from the database.
        current_stock (int): Current stock level for the product.

    Returns:
        str: Advice message from inventory management.
    """
    # 1️⃣ Check peak season
    peak_season = detect_peak_season(product.id)

    # 2️⃣ Generate forecast for next 4 periods
    forecast_data = generate_forecast(product.id, periods=4)


    total_forecast = sum(item['yhat'] for item in forecast_data) if forecast_data else 0

    # 3️⃣ Build advice messages
    advice = []

    # Stock is too low for expected demand
    if current_stock < (total_forecast * 0.5):
        advice.append(f"⚠️ Stock is critically low compared to upcoming demand in {peak_season}.")
        advice.append("Consider reordering immediately to avoid stockouts.")

    
    elif current_stock < total_forecast:
        advice.append("ℹ️ Stock is below forecasted demand for {peak_season}.")
        advice.append("Plan for partial restocking to meet demand.")

    
    else:
        advice.append(f"✅ Stock is sufficient to meet upcoming demand in {peak_season}.")
        advice.append("No immediate action required.")

    return " ".join(advice)