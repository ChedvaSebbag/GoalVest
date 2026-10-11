"""GoalVest Flask application factory."""
from flask import Flask
from flask_cors import CORS

from .config import Config


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})

    # Controllers (MVC) – Blueprint לכל אזור. נוספים לפי docs/08-api-spec.md
    from .controllers.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    return app
