net start MySQL
mysql -u root -p
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
flask db migrate -m "Add customer_name to Transaction"
flask db upgrade
flask db migrate -m "Initial migration"
flask db upgrade
flask db init
set FLASK_APP=APP
flask run --host=127.0.0.1
flask db migrate -m "Add user_id to Transaction"
flask db upgrade
python seed_products.py
git init
git remote add origin https://github.com/rowin0222-maker/seasonal-insight-system.git
git add .
git commit -m "Initial commit of my system"
git branch -M main
git push -u origin main
git add requirements.txt Procfile
git commit -m "Add requirements and Procfile for deployment"
git push origin main
git add Procfile
git commit -m "Fix Procfile format"
web:: https://seasonal-insight-system.onrender.com
gunicorn run:app
web: gunicorn "run:create_app()"