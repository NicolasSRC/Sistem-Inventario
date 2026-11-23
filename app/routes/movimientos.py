from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from .. import db
from ..models import Producto, Movimiento, Proveedor
from ..services.inventario import (
    InventarioError,
    registrar_ajuste,
    registrar_entrada,
    registrar_salida,
)
from ..utils import admin_required

bp = Blueprint("movimientos", __name__, url_prefix="/movimientos")

TIPOS = ("entrada", "salida", "ajuste", "merma")


@bp.route("/")
@login_required
def historial():
    tipo = request.args.get("tipo", "")
    q = Movimiento.query
    if tipo in TIPOS:
        q = q.filter_by(tipo=tipo)
    return render_template("movimientos/historial.html",
                           movimientos=q.order_by(Movimiento.fecha.desc()).all(), tipo=tipo)


@bp.route("/venta", methods=["GET", "POST"])
@login_required
def venta():
    productos = (Producto.query
                 .filter(Producto.activo.is_(True), Producto.cantidad > 0)
                 .order_by(Producto.nombre)
                 .all())

    if request.method == "POST":
        p = db.session.get(Producto, request.form.get("producto_id", type=int) or 0)
        cantidad = request.form.get("cantidad", type=int)
        observacion = request.form.get("observacion", "").strip()

        if not p or not cantidad or cantidad <= 0:
            flash("Seleccione un producto y una cantidad mayor a 0.", "danger")
            return redirect(url_for("movimientos.venta"))
        if not p.activo:
            flash("El producto está inactivo; no se puede vender.", "danger")
            return redirect(url_for("movimientos.venta"))

        try:
            movimientos = registrar_salida(
                p,
                cantidad,
                motivo="venta",
                observacion=observacion,
                usuario=current_user,
            )
        except InventarioError as e:
            db.session.rollback()
            flash(str(e), "danger")
        else:
            total = cantidad * (p.precio or 0)
            lotes = [m.lote.codigo for m in movimientos if m.lote]
            mensaje = ("Venta registrada: %d × %s por $%s. Stock restante: %d."
                       % (cantidad, p.nombre, format(total, ",.2f"), p.cantidad))
            if lotes:
                mensaje += " Lotes consumidos: %s." % ", ".join(lotes)
            flash(mensaje, "success")
            return redirect(url_for("movimientos.venta"))

    return render_template("movimientos/venta.html", productos=productos)


@bp.route("/registrar", methods=["GET", "POST"])
@admin_required
def registrar():
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    proveedores = Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all()
    contexto = {"productos": productos, "proveedores": proveedores}

    if request.method == "POST":
        p = db.session.get(Producto, request.form.get("producto_id", type=int) or 0)
        tipo = request.form.get("tipo")
        cantidad = request.form.get("cantidad", type=int)
        observacion = request.form.get("observacion", "").strip()

        if not p or tipo not in ("entrada", "salida") or not cantidad or cantidad <= 0:
            flash("Seleccione producto, tipo y una cantidad mayor a 0.", "danger")
            return render_template("movimientos/registrar.html", **contexto)
        if not p.activo:
            flash("El producto está inactivo; reactívelo antes de mover stock.", "danger")
            return render_template("movimientos/registrar.html", **contexto)

        try:
            if tipo == "entrada":
                proveedor = None
                proveedor_id = request.form.get("proveedor_id")
                if proveedor_id:
                    try:
                        proveedor = db.session.get(Proveedor, int(proveedor_id))
                    except (TypeError, ValueError):
                        proveedor = None

                movimiento = registrar_entrada(
                    p,
                    cantidad,
                    costo_unitario=request.form.get("costo_unitario"),
                    proveedor=proveedor,
                    actualizar_costo=bool(request.form.get("actualizar_costo")),
                    observacion=observacion,
                    usuario=current_user,
                    lote_codigo=request.form.get("lote_codigo"),
                    fecha_vencimiento=request.form.get("fecha_vencimiento"),
                )
                mensaje = ("Entrada registrada. Stock actual: %d. Costo promedio: $%s."
                           % (p.cantidad, format(p.precio_compra or 0, ",.2f")))
                if movimiento.lote:
                    mensaje += " Lote %s con vencimiento %s." % (
                        movimiento.lote.codigo,
                        movimiento.lote.fecha_vencimiento.strftime("%d/%m/%Y"),
                    )
                flash(mensaje, "success")
            else:
                movimientos = registrar_salida(
                    p,
                    cantidad,
                    motivo="venta",
                    observacion=observacion,
                    usuario=current_user,
                )
                lotes = [m.lote.codigo for m in movimientos if m.lote]
                mensaje = "Salida registrada. Stock actual de %s: %d." % (p.nombre, p.cantidad)
                if lotes:
                    mensaje += " Lotes consumidos: %s." % ", ".join(lotes)
                flash(mensaje, "success")
            return redirect(url_for("movimientos.registrar"))
        except InventarioError as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template("movimientos/registrar.html", **contexto)


@bp.route("/ajuste", methods=["GET", "POST"])
@admin_required
def ajuste():
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    contexto = {"productos": productos}

    if request.method == "POST":
        p = db.session.get(Producto, request.form.get("producto_id", type=int) or 0)
        tipo = request.form.get("tipo")
        cantidad = request.form.get("cantidad", type=int)
        motivo = request.form.get("motivo", "")
        direccion = request.form.get("direccion", "disminuir")
        observacion = request.form.get("observacion", "").strip()

        if not p or tipo not in ("merma", "ajuste") or not cantidad or cantidad <= 0:
            flash("Seleccione producto, operación y una cantidad mayor a 0.", "danger")
            return render_template("movimientos/ajuste.html", **contexto)
        if not p.activo:
            flash("El producto está inactivo; reactívelo antes de ajustar stock.", "danger")
            return render_template("movimientos/ajuste.html", **contexto)

        delta = -cantidad if tipo == "merma" or direccion != "aumentar" else cantidad
        try:
            movimientos = registrar_ajuste(
                p, delta, motivo=motivo, observacion=observacion,
                usuario=current_user, tipo=tipo,
            )
        except InventarioError as e:
            db.session.rollback()
            flash(str(e), "danger")
        else:
            impacto = sum(m.impacto or 0 for m in movimientos)
            if tipo == "merma":
                mensaje = "Merma registrada. Stock actual de %s: %d. Impacto: $%s."
            else:
                mensaje = "Ajuste registrado. Stock actual de %s: %d. Impacto: $%s."
            flash(mensaje % (p.nombre, p.cantidad, format(impacto, ",.2f")), "success")
            return redirect(url_for("movimientos.ajuste"))

    return render_template("movimientos/ajuste.html", **contexto)
