from prophet import Prophet
import pandas as pd
from app.models import Transaction

def generate_forecast(product_id, periods=10):
    """
    Generates a sales forecast for a given product using Prophet.

    Args:
        product_id (int): ID of the product
        periods (int): Number of future periods (days) to predict.
    
    Returns:
        list: Forecast data containing 'ds' (date) and 'yhat' (predicted value).
    """

    transactions = Transaction.query.filter_by(product_id=product_id).all()


    if not transactions:
        return []


    data = [{'ds': t.date, 'y': t.quantity} for t in transactions if t.date and t.quantity is not None]
    df = pd.DataFrame(data)


    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = pd.to_numeric(df['y'], errors='coerce')
    df.dropna(inplace=True)
    df = df[df['y'] >= 0]


    if len(df) < 2:
        return [{"ds": None, "yhat": 0}]


    model = Prophet()
    model.fit(df)


    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)


    return forecast[['ds', 'yhat']].tail(periods).to_dict(orient='records')