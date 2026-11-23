import csv, io
from flask import Blueprint, render_template, Response
from ..models import Lote, Movimiento, Producto
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
    filas = [["ID", "Nombre", "SKU", "Código de barras", "Categoría", "Proveedor", "Precio", "Cantidad", "Stock mínimo", "Valor total", "Estado"]]
    for p in Producto.query.order_by(Producto.nombre):
        filas.append([p.id, p.nombre, p.sku or "", p.codigo_barras or "",
                      p.categoria.nombre if p.categoria else "",
                      p.proveedor.nombre if p.proveedor else "",
                      p.precio, p.cantidad, p.stock_minimo, round(p.precio * p.cantidad, 2),
                      "Activo" if p.activo else "Inactivo"])
    return _csv("productos", filas)


@bp.route("/movimientos.csv")
@admin_required
def movimientos():
    filas = [["ID", "Fecha", "Producto", "Tipo", "Motivo", "Cantidad", "Efecto", "Lote", "Vencimiento",
              "Costo unitario", "Impacto", "Stock anterior", "Stock nuevo", "Usuario", "Observación"]]
    for m in Movimiento.query.order_by(Movimiento.fecha.desc()):
        filas.append([m.id, m.fecha.strftime("%Y-%m-%d %H:%M"), m.producto.nombre,
                      m.tipo, m.motivo or "", m.cantidad, m.efecto,
                      m.lote.codigo if m.lote else "",
                      m.lote.fecha_vencimiento.strftime("%Y-%m-%d") if m.lote and m.lote.fecha_vencimiento else "",
                      m.costo_unitario or 0, m.impacto or 0,
                      m.stock_anterior if m.stock_anterior is not None else "",
                      m.stock_nuevo if m.stock_nuevo is not None else "",
                      m.usuario.username if m.usuario else "", m.observacion or ""])
    return _csv("movimientos", filas)


@bp.route("/mermas.csv")
@admin_required
def mermas():
    filas = [["ID", "Fecha", "Producto", "Motivo", "Cantidad", "Costo unitario",
              "Impacto", "Usuario", "Observación"]]
    consulta = (Movimiento.query.filter(Movimiento.tipo == "merma")
                .order_by(Movimiento.fecha.desc()))
    for m in consulta:
        filas.append([m.id, m.fecha.strftime("%Y-%m-%d %H:%M"), m.producto.nombre,
                      m.motivo or "", m.cantidad, m.costo_unitario or 0, m.impacto or 0,
                      m.usuario.username if m.usuario else "", m.observacion or ""])
    return _csv("mermas", filas)


@bp.route("/lotes.csv")
@admin_required
def lotes():
    filas = [["Producto", "SKU", "Lote", "Vencimiento", "Días para vencer", "Cantidad inicial",
              "Cantidad actual", "Costo unitario", "Valor", "Estado"]]
    consulta = (Lote.query.join(Producto)
                .filter(Producto.activo.is_(True), Lote.cantidad_actual > 0)
                .order_by(Lote.fecha_vencimiento.is_(None), Lote.fecha_vencimiento, Lote.id))
    for l in consulta:
        if l.vencido:
            estado = "Vencido"
        elif l.por_vencer:
            estado = "Por vencer"
        elif l.fecha_vencimiento:
            estado = "Vigente"
        else:
            estado = "Sin fecha"
        filas.append([l.producto.nombre, l.producto.sku or "", l.codigo or "",
                      l.fecha_vencimiento.strftime("%Y-%m-%d") if l.fecha_vencimiento else "",
                      l.dias_para_vencer if l.dias_para_vencer is not None else "",
                      l.cantidad_inicial, l.cantidad_actual, l.costo_unitario or 0,
                      round((l.cantidad_actual or 0) * (l.costo_unitario or 0), 2), estado])
    return _csv("lotes", filas)
