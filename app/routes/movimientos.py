from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Producto, Movimiento
from ..utils import admin_required

bp = Blueprint("movimientos", __name__, url_prefix="/movimientos")


@bp.route("/")
@login_required
def historial():
    tipo = request.args.get("tipo", "")
    q = Movimiento.query
    if tipo in ("entrada", "salida"):
        q = q.filter_by(tipo=tipo)
    return render_template("movimientos/historial.html",
                           movimientos=q.order_by(Movimiento.fecha.desc()).all(), tipo=tipo)


@bp.route("/registrar", methods=["GET", "POST"])
@admin_required
def registrar():
    if request.method == "POST":
        p = db.session.get(Producto, request.form.get("producto_id", type=int) or 0)
        tipo = request.form.get("tipo")
        cant = request.form.get("cantidad", type=int)
        if not p or tipo not in ("entrada", "salida") or not cant or cant <= 0:
            flash("Seleccione producto, tipo y una cantidad mayor a 0.", "danger")
        elif tipo == "salida" and cant > p.cantidad:
            flash("Stock insuficiente: disponible %d, solicitado %d." % (p.cantidad, cant), "danger")
        else:
            p.cantidad += cant if tipo == "entrada" else -cant
            db.session.add(Movimiento(producto_id=p.id, usuario_id=current_user.id, tipo=tipo,
                                      cantidad=cant, observacion=request.form.get("observacion", "").strip()))
            db.session.commit()
            flash("%s registrada. Stock actual de %s: %d." % (tipo.capitalize(), p.nombre, p.cantidad), "success")
            return redirect(url_for("movimientos.registrar"))
    return render_template("movimientos/registrar.html", productos=Producto.query.order_by(Producto.nombre).all())
