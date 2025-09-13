from flask import Flask
from app.extensions import db, bcrypt
from app.routes import main
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.consumer import oauth_authorized
from flask_login import LoginManager
from app.models import User, Product
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:ROWINalan8096?@localhost/seasonal_insight_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    app.debug = True
    app.config['ENV'] = 'development'


    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    
    from app.advice.routes import advice_bp
    app.register_blueprint(advice_bp, url_prefix="/advice")
    app.register_blueprint(main)

    
    # OAuth with Google
    google_bp = make_google_blueprint(
        client_id="YOUR_GOOGLE_CLIENT_ID",
        client_secret="YOUR_GOOGLE_CLIENT_SECRET",
        redirect_url="/google_login",
        scope=["profile", "email"],
    )

    if "google" not in app.blueprints:
        app.register_blueprint(google_bp, url_prefix="/login/google")

    # ✅ Auto-seed products when app starts
    def seed_products():
        products = [
            {"barcode": "4800016551219", "name": "Fita Crackers", "price": 12.50, "unit": "pack", "stock": 100, "category": "Snacks"},
            {"barcode": "4801981111111", "name": "Coca-Cola 1.5L", "price": 75.00, "unit": "bottle", "stock": 50, "category": "Beverages"},
            {"barcode": "4801981222222", "name": "Sprite 1.5L", "price": 72.00, "unit": "bottle", "stock": 50, "category": "Beverages"},
            {"barcode": "4801981333333", "name": "Nescafe 3-in-1", "price": 8.00, "unit": "sachet", "stock": 200, "category": "Coffee"},
            {"barcode": "4801981444444", "name": "Lucky Me Pancit Canton", "price": 18.00, "unit": "pack", "stock": 150, "category": "Instant Noodles"},
        ]
        for p in products:
            if not Product.query.filter_by(barcode=p["barcode"]).first():
                db.session.add(Product(**p, date_added=datetime.utcnow()))
        db.session.commit()

    with app.app_context():
        seed_products()

    # Register blueprints

    return app
