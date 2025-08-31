from app import create_app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        from app.extensions import db
        db.drop_all()
        db.create_all()
        print("✅ Database dropped and recreated successfully.")
        
    app.run(debug=True, port=5000)