import csv, io
from flask import Blueprint, render_template, Response
from ..models import Producto, Movimiento
from ..utils import admin_required

bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _csv(nombre, filas):
    buf = io.StringIO()
    csv.writer(buf).writerows(filas)
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=%s.csv" % nombre})


@bp.route("/")
@admin_required
def index():
    return render_template("reportes/index.html")


@bp.route("/productos.csv")
@admin_required
def productos():
    filas = [["ID", "Nombre", "SKU", "Categoría", "Precio", "Cantidad", "Stock mínimo", "Valor total"]]
    for p in Producto.query.order_by(Producto.nombre):
        filas.append([p.id, p.nombre, p.sku or "", p.categoria.nombre if p.categoria else "",
                      p.precio, p.cantidad, p.stock_minimo, round(p.precio * p.cantidad, 2)])
    return _csv("productos", filas)


@bp.route("/movimientos.csv")
@admin_required
def movimientos():
    filas = [["ID", "Fecha", "Producto", "Tipo", "Cantidad", "Usuario", "Observación"]]
    for m in Movimiento.query.order_by(Movimiento.fecha.desc()):
        filas.append([m.id, m.fecha.strftime("%Y-%m-%d %H:%M"), m.producto.nombre, m.tipo,
                      m.cantidad, m.usuario.username if m.usuario else "", m.observacion or ""])
    return _csv("movimientos", filas)
