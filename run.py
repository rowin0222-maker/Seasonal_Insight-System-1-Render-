from app import create_app
from flask import Flask

app = create_app()

@app.route("/")
def home():
    return "Hello, Railway!"