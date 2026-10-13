import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicie sesión para continuar."
    login_manager.login_message_category = "warning"

    from .routes import auth, productos, categorias, movimientos, dashboard, reportes
    for m in (auth, productos, categorias, movimientos, dashboard, reportes):
        app.register_blueprint(m.bp)

    with app.app_context():
        from .models import Usuario, Categoria
        db.create_all()
        if not Usuario.query.first():  # datos iniciales
            for u, p, r in (("admin", "admin123", "administrador"), ("cliente", "cliente123", "cliente")):
                x = Usuario(username=u, rol=r)
                x.set_password(p)
                db.session.add(x)
            for n in ("General", "Electrónica", "Papelería", "Hogar"):
                db.session.add(Categoria(nombre=n))
            db.session.commit()
    return app
