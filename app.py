from flask import Flask
from database.setup_database import init_db
from routes.main_routes import main_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.password_reset_routes import password_reset_bp
from routes.prediction_routes import prediction_bp
from routes.chatbot_routes import chatbot_bp
from routes.transaction_history_routes import transaction_history_bp

app = Flask(__name__)
app.secret_key = "civic_plan_secret_key"

init_db()
#ammo hucnwa
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(password_reset_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(transaction_history_bp)

if __name__ == "__main__":
    app.run(debug=True)