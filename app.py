from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, User

def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes import auth, events, sms_webhook, dashboard
    app.register_blueprint(auth.bp)
    app.register_blueprint(events.bp)
    app.register_blueprint(sms_webhook.bp)
    app.register_blueprint(dashboard.bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
