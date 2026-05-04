from __future__ import annotations

from pathlib import Path
import os

from authlib.integrations.flask_client import OAuth
from flask import Flask

from .extensions import db


oauth = OAuth()


def _migrate_sqlite_schema(app: Flask) -> None:
    if not app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite:"):
        return

    engine = db.engine
    with engine.begin() as connection:
        columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(portfolio)")]
        if "user_id" not in columns:
            connection.exec_driver_sql("ALTER TABLE portfolio ADD COLUMN user_id INTEGER")

        user_row = connection.exec_driver_sql("SELECT id FROM user ORDER BY id ASC LIMIT 1").first()
        if user_row is not None:
            owner_id = user_row[0]
        else:
            connection.exec_driver_sql(
                """
                INSERT INTO user (provider, provider_sub, email, name, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                ("local", "legacy", None, "Legacy User"),
            )
            owner_id = connection.exec_driver_sql("SELECT id FROM user ORDER BY id DESC LIMIT 1").scalar_one()

        connection.exec_driver_sql(
            "UPDATE portfolio SET user_id = ? WHERE user_id IS NULL",
            (owner_id,),
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_portfolio_user_id ON portfolio (user_id)"
        )


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    instance_path = Path(app.instance_path)
    database_path = instance_path / "portfolio.db"

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", f"sqlite:///{database_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        FINNHUB_API_KEY=os.getenv("FINNHUB_API_KEY"),
        OAUTH_PROVIDER_NAME=os.getenv("OAUTH_PROVIDER_NAME", "google"),
        OAUTH_CLIENT_ID=os.getenv("OAUTH_CLIENT_ID"),
        OAUTH_CLIENT_SECRET=os.getenv("OAUTH_CLIENT_SECRET"),
        OAUTH_REDIRECT_URI=os.getenv("OAUTH_REDIRECT_URI", "http://127.0.0.1:5000/auth/callback"),
        OAUTH_SERVER_METADATA_URL=os.getenv(
            "OAUTH_SERVER_METADATA_URL",
            "https://accounts.google.com/.well-known/openid-configuration",
        ),
        OAUTH_SCOPE=os.getenv("OAUTH_SCOPE", "openid email profile"),
    )

    if test_config:
        app.config.update(test_config)

    instance_path.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    oauth.init_app(app)

    if app.config.get("OAUTH_CLIENT_ID") and app.config.get("OAUTH_CLIENT_SECRET"):
        oauth.register(
            name=app.config["OAUTH_PROVIDER_NAME"],
            client_id=app.config["OAUTH_CLIENT_ID"],
            client_secret=app.config["OAUTH_CLIENT_SECRET"],
            server_metadata_url=app.config["OAUTH_SERVER_METADATA_URL"],
            client_kwargs={"scope": app.config["OAUTH_SCOPE"]},
        )
    else:
        app.logger.warning("OAUTH_CLIENT_ID or OAUTH_CLIENT_SECRET not set; skipping OAuth registration")

    from . import models  # noqa: F401
    from .routes import bp

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        _migrate_sqlite_schema(app)

    return app