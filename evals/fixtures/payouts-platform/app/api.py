from flask import Flask

from app import sellers, webhooks


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(webhooks.bp)
    app.register_blueprint(sellers.bp)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
