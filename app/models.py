from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # administrador | cliente

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p):
        return check_password_hash(self.password_hash, p)

    @property
    def es_admin(self):
        return self.rol == "administrador"


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    productos = db.relationship("Producto", backref="categoria", lazy=True)


class Producto(db.Model):
    __tablename__ = "productos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"))
    stock_minimo = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.now)
    movimientos = db.relationship("Movimiento", backref="producto", lazy=True,
                                  cascade="all, delete-orphan")

    @property
    def bajo_stock(self):
        return (self.cantidad or 0) <= (self.stock_minimo or 0)


class Movimiento(db.Model):
    __tablename__ = "movimientos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    tipo = db.Column(db.String(10), nullable=False)  # entrada | salida
    cantidad = db.Column(db.Integer, nullable=False)
    observacion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship("Usuario", backref="movimientos")


@login_manager.user_loader
def load_user(uid):
    return db.session.get(Usuario, int(uid))
