import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from app.models import Transaction
from app import db
from .season import determine_season
from dateutil.relativedelta import relativedelta
from calendar import monthrange

def generate_forecast(product, forecast_unit: str, how_many: int, current_stock: int = 0):
    past_transactions = Transaction.query.filter_by(product_id=product.id).order_by(Transaction.date).all()
    
    if not past_transactions:
        return [], [], []
    

    latest_date = past_transactions[-1].date
    last_quantity = past_transactions[-1].quantity
    product_name = product.name


    grouped = defaultdict(list)
    for tx in past_transactions:
        tx_date = tx.date

        if forecast_unit == "week":
            key = (tx_date.year, tx_date.isocalendar()[1])
        elif forecast_unit == "month":
            key = (tx_date.year, tx_date.month)
        elif forecast_unit == "year":
            key = tx_date.year
        else:
            key = tx_date
        grouped[key].append(tx.quantity)

    if not grouped:
        return [], [], []


    avg_quantity = round(sum(sum(qs) for qs in grouped.values()) / len(grouped))
    stock_left = current_stock


    labels = [latest_date.strftime('%Y-%m-%d %H:%M')]
    values = [last_quantity]
    table_data = [{
        'date': labels[0],
        'forecast': last_quantity,
        'stock_left': current_stock,
        'recommended_season': determine_season(product_name, latest_date)
    }]


    for i in range(1, how_many + 1):
        if forecast_unit == "week":
            forecast_date = latest_date + timedelta(weeks=i)

        elif forecast_unit == "month":
            base_month_date = latest_date + relativedelta(months=i)

            first_day_of_month = base_month_date.replace(day=1)


            weekday_target = latest_date.weekday()
            days_to_add = (weekday_target - first_day_of_month.weekday()) % 7
            forecast_date = first_day_of_month + timedelta(days=days_to_add)


        elif forecast_unit == "year":
            base_year_date = latest_date + relativedelta(years=i)
            first_day_of_month = base_year_date.replace(day=1, month=latest_date.month)

            weekday_target = latest_date.weekday()
            days_to_add = (weekday_target - first_day_of_month.weekday()) % 7
            forecast_date = first_day_of_month + timedelta(days=days_to_add)

        else:
            continue

        forecast_date = forecast_date.replace(hour=latest_date.hour, minute=latest_date.minute)
        season = determine_season(product_name, forecast_date)


        if forecast_unit == 'week':
            trend_key = (forecast_date.year, forecast_date.isocalendar()[1])
        elif forecast_unit == 'month':
            trend_key =(forecast_date.year, forecast_date.month)
        elif forecast_unit == 'year':
            trend_key = forecast_date.year
        else:
            trend_key = None
        import random
        if trend_key in grouped:
            forecast_value = round(sum(grouped[trend_key]) / len(grouped[trend_key]))
        else:
            # Add variation instead of repeating avg_quantity
            variation = random.uniform(0.9, 1.15) # ±15% fluctuation
            forecast_value = max(1, round(avg_quantity * variation))

        stock_left -= forecast_value

        labels.append(forecast_date.strftime('%Y-%m-%d %H:%M'))
        values.append(forecast_value)
        table_data.append({
            'date': forecast_date.strftime('%Y-%m-%d %H:%M'),
            'forecast': forecast_value,
            'stock_left': max(stock_left, 0),
            'recommended_season': season
        })
    
    return labels, values, table_data