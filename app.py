from flask import Flask
from database.setup_database import init_db
from routes.main_routes import main_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp

app = Flask(__name__)
app.secret_key = "civic_plan_secret_key"

init_db()

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)

if __name__ == "__main__":
    app.run(debug=True)