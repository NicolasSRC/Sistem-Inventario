from datetime import date, datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


class Sucursal(db.Model):
    __tablename__ = "sucursales"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(30))
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=datetime.now)


class Proveedor(db.Model):
    __tablename__ = "proveedores"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    nit = db.Column(db.String(30))
    contacto = db.Column(db.String(120))
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    lead_time_dias = db.Column(db.Integer, nullable=False, default=3, server_default="3")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=datetime.now)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # tendero | cajero
    sucursal_id = db.Column(db.Integer, db.ForeignKey("sucursales.id"))
    sucursal = db.relationship("Sucursal", backref=db.backref("usuarios", lazy=True))

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p):
        return check_password_hash(self.password_hash, p)

    @property
    def es_tendero(self):
        return self.rol in ("tendero", "administrador")

    @property
    def es_admin(self):
        """Alias de compatibilidad con el código y las plantillas existentes."""
        return self.es_tendero

    @property
    def es_cajero(self):
        return self.rol in ("cajero", "cliente")


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
    codigo_barras = db.Column(db.String(64), unique=True, index=True)
    precio = db.Column(db.Float, nullable=False)  # precio de venta
    precio_compra = db.Column(db.Float, nullable=False, default=0, server_default="0")
    cantidad = db.Column(db.Integer, default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"))
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"))
    sucursal_id = db.Column(db.Integer, db.ForeignKey("sucursales.id"), nullable=False)
    stock_minimo = db.Column(db.Integer, default=5)
    dias_alerta_vencimiento = db.Column(db.Integer, nullable=False, default=15, server_default="15")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=datetime.now)

    proveedor = db.relationship("Proveedor", backref=db.backref("productos", lazy=True))
    sucursal = db.relationship("Sucursal", backref=db.backref("productos", lazy=True))
    movimientos = db.relationship("Movimiento", backref="producto", lazy=True,
                                  cascade="all, delete-orphan")
    lotes = db.relationship("Lote", backref="producto", lazy=True,
                            cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_productos_nombre", "nombre"),
        db.Index("ix_productos_sucursal", "sucursal_id"),
    )

    @property
    def bajo_stock(self):
        return (self.cantidad or 0) <= (self.stock_minimo or 0)

    @property
    def margen(self):
        if not self.precio:
            return 0
        return ((self.precio - (self.precio_compra or 0)) / self.precio) * 100


class Lote(db.Model):
    __tablename__ = "lotes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    sucursal_id = db.Column(db.Integer, db.ForeignKey("sucursales.id"), nullable=False)
    codigo = db.Column(db.String(50))
    fecha_vencimiento = db.Column(db.Date)
    cantidad_inicial = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    cantidad_actual = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    costo_unitario = db.Column(db.Float, nullable=False, default=0, server_default="0")
    created_at = db.Column(db.DateTime, default=datetime.now)

    sucursal = db.relationship("Sucursal", backref=db.backref("lotes", lazy=True))

    __table_args__ = (
        db.UniqueConstraint("producto_id", "codigo", name="uq_lotes_producto_codigo"),
        db.Index("ix_lotes_fecha_vencimiento", "fecha_vencimiento"),
        db.Index("ix_lotes_sucursal", "sucursal_id"),
    )

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < date.today())

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - date.today()).days

    @property
    def por_vencer(self):
        if not self.fecha_vencimiento or not self.cantidad_actual:
            return False
        dias = self.producto.dias_alerta_vencimiento or 15
        return not self.vencido and self.fecha_vencimiento <= date.today() + timedelta(days=dias)


class Movimiento(db.Model):
    __tablename__ = "movimientos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"))
    sucursal_id = db.Column(db.Integer, db.ForeignKey("sucursales.id"), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # entrada | salida | ajuste | merma
    motivo = db.Column(db.String(30))  # compra | venta | vencimiento | dano | diferencia_conteo...
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Float)
    impacto = db.Column(db.Float)
    stock_anterior = db.Column(db.Integer)
    stock_nuevo = db.Column(db.Integer)
    delta = db.Column(db.Integer)
    observacion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.now)

    usuario = db.relationship("Usuario", backref="movimientos")
    lote = db.relationship("Lote", backref=db.backref("movimientos", lazy=True))
    sucursal = db.relationship("Sucursal", backref=db.backref("movimientos", lazy=True))

    __table_args__ = (
        db.Index("ix_movimientos_fecha", "fecha"),
        db.Index("ix_movimientos_producto_fecha", "producto_id", "fecha"),
        db.Index("ix_movimientos_sucursal", "sucursal_id"),
    )

    @property
    def efecto(self):
        """Efecto neto del movimiento sobre el stock."""
        if self.tipo == "entrada":
            return self.cantidad
        if self.tipo in ("salida", "merma"):
            return -self.cantidad
        return self.delta or 0


@login_manager.user_loader
def load_user(uid):
    return db.session.get(Usuario, int(uid))
