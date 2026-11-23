from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..models import Proveedor
from ..utils import admin_required

bp = Blueprint("proveedores", __name__, url_prefix="/proveedores")


def _email_valido(email):
    if not email:
        return True
    if "@" not in email:
        return False
    dominio = email.rsplit("@", 1)[-1]
    return "." in dominio and not dominio.startswith(".") and not dominio.endswith(".")


def _guardar(proveedor):
    f = request.form
    nombre = f.get("nombre", "").strip()
    email = f.get("email", "").strip()
    try:
        lead_time = int(f.get("lead_time_dias") or 3)
    except ValueError:
        lead_time = -1

    if not nombre:
        flash("El nombre del proveedor es obligatorio.", "danger")
        return False
    if lead_time < 0:
        flash("El tiempo de entrega debe ser un número mayor o igual a 0.", "danger")
        return False
    if not _email_valido(email):
        flash("El correo electrónico no es válido.", "danger")
        return False

    consulta = Proveedor.query.filter(db.func.lower(Proveedor.nombre) == nombre.lower())
    if proveedor.id:
        consulta = consulta.filter(Proveedor.id != proveedor.id)
    if consulta.first():
        flash("Ya existe un proveedor con ese nombre.", "danger")
        return False

    proveedor.nombre = nombre[:120]
    proveedor.nit = f.get("nit", "").strip()[:30]
    proveedor.contacto = f.get("contacto", "").strip()[:120]
    proveedor.telefono = f.get("telefono", "").strip()[:30]
    proveedor.email = email[:120]
    proveedor.direccion = f.get("direccion", "").strip()[:200]
    proveedor.lead_time_dias = lead_time
    db.session.add(proveedor)
    db.session.commit()
    return True


@bp.route("/")
@admin_required
def lista():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    consulta = Proveedor.query
    if q:
        like = "%" + q + "%"
        consulta = consulta.filter(db.or_(
            Proveedor.nombre.ilike(like),
            Proveedor.nit.ilike(like),
            Proveedor.contacto.ilike(like),
            Proveedor.email.ilike(like),
        ))
    if estado == "activos":
        consulta = consulta.filter_by(activo=True)
    elif estado == "inactivos":
        consulta = consulta.filter_by(activo=False)

    return render_template(
        "proveedores/lista.html",
        proveedores=consulta.order_by(Proveedor.activo.desc(), Proveedor.nombre).all(),
        q=q,
        estado=estado,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST" and _guardar(Proveedor()):
        flash("Proveedor registrado correctamente.", "success")
        return redirect(url_for("proveedores.lista"))
    return render_template("proveedores/form.html", proveedor=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar(id):
    proveedor = db.get_or_404(Proveedor, id)
    if request.method == "POST" and _guardar(proveedor):
        flash("Proveedor actualizado.", "success")
        return redirect(url_for("proveedores.lista"))
    return render_template("proveedores/form.html", proveedor=proveedor)


@bp.route("/<int:id>/estado", methods=["POST"])
@admin_required
def cambiar_estado(id):
    proveedor = db.get_or_404(Proveedor, id)
    proveedor.activo = not proveedor.activo
    db.session.commit()
    if proveedor.activo:
        flash("Proveedor «%s» activado." % proveedor.nombre, "success")
    else:
        flash("Proveedor «%s» desactivado. Sus productos conservan la referencia." % proveedor.nombre, "warning")
    return redirect(url_for("proveedores.lista"))
