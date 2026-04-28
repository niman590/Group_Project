from flask import Flask
from flask_talisman import Talisman
from database.setup_database import init_db

from routes.main_routes import main_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.admin_planning_application_routes import admin_planning_bp
from routes.password_reset_routes import password_reset_bp
from routes.prediction_routes import prediction_bp
from routes.chatbot_routes import chatbot_bp
from routes.transaction_history_routes import transaction_history_bp
from routes.submit_documents_routes import submit_documents_bp
from routes.support_documents_routes import support_documents_bp
from routes.admin_reports_routes import admin_reports_bp


app = Flask(__name__)

Talisman(
    app,
    frame_options="DENY",
    content_security_policy=None,
    force_https=False
)

app.secret_key = "civic_plan_secret_key"

init_db()

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_planning_bp)
app.register_blueprint(password_reset_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(transaction_history_bp)
app.register_blueprint(submit_documents_bp)
app.register_blueprint(support_documents_bp)
app.register_blueprint(admin_reports_bp)


if __name__ == "__main__":
    app.run(debug=True)