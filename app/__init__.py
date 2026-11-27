import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, render_as_batch=True, compare_type=True)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicie sesión para continuar."
    login_manager.login_message_category = "warning"

    from .routes import auth, productos, categorias, movimientos, dashboard, reportes, proveedores, lotes, sucursales, admin
    for m in (auth, productos, categorias, movimientos, dashboard, reportes, proveedores, lotes, sucursales, admin):
        app.register_blueprint(m.bp)

    @app.context_processor
    def contexto_sucursal():
        from flask_login import current_user
        from .services.sucursales import sucursal_actual, sucursales_activas

        if not current_user.is_authenticated:
            return {"sucursal_actual": None, "sucursales": []}
        return {
            "sucursal_actual": sucursal_actual(),
            "sucursales": sucursales_activas() if current_user.es_admin else [],
        }

    # Registra todos los modelos en los metadatos de SQLAlchemy/Alembic.
    from . import models  # noqa: F401

    from .cli import init_db_command, seed_base_command
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_base_command)

    return app
