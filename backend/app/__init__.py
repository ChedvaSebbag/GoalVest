"""GoalVest Flask application factory."""
from flask import Flask
from flask_cors import CORS
from flask_limiter.errors import RateLimitExceeded

from .auth.jwt import init_jwt
from .auth.limiter import limiter
from .bootstrap import build_dispatcher
from .config import Config
from .controllers.errors import error_response
from .infrastructure.db import close_db


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    app.json.ensure_ascii = False
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    init_jwt(app)
    limiter.init_app(app)
    app.extensions["projections"] = build_dispatcher()
    app.teardown_appcontext(close_db)

    @app.errorhandler(RateLimitExceeded)
    def rate_limited(_exc: RateLimitExceeded):
        return error_response(429, "RATE_LIMITED", "יותר מדי ניסיונות התחברות. נסו שוב בעוד מספר דקות.")

    # Controllers (MVC) – Blueprint לכל אזור. נוספים לפי docs/08-api-spec.md
    from .controllers.agent_leads import agent_leads_bp
    from .controllers.auth import auth_bp
    from .controllers.health import health_bp
    from .controllers.investor import investor_bp
    from .controllers.notifications import notifications_bp
    from .controllers.products import products_bp
    from .controllers.requests import requests_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(investor_bp, url_prefix="/api")
    app.register_blueprint(requests_bp, url_prefix="/api")
    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(agent_leads_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    return app
