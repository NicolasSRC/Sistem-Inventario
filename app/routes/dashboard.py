from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from .. import db
from ..models import Producto, Movimiento

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def index():
    total = Producto.query.count()
    unidades = db.session.query(func.coalesce(func.sum(Producto.cantidad), 0)).scalar()
    valor = db.session.query(func.coalesce(func.sum(Producto.precio * Producto.cantidad), 0)).scalar()
    alertas = Producto.query.filter(Producto.cantidad <= Producto.stock_minimo).count()
    ultimos = Movimiento.query.order_by(Movimiento.fecha.desc()).limit(5).all()
    return render_template("dashboard.html", total=total, unidades=unidades,
                           valor=valor, alertas=alertas, ultimos=ultimos)
