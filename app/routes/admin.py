"""Panel administrativo: gestión de usuarios y sucursales.

Solo el tendero (administrador) puede acceder. Los usuarios no se eliminan:
se editan para conservar la trazabilidad de sus movimientos.
"""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from .. import db
from ..models import Movimiento, Producto, Sucursal, Usuario
from ..services.sucursales import CLAVE_SESION
from ..utils import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLES = {
    "tendero": "Tendero (administrador)",
    "cajero": "Cajero",
}


def _sucursales_formulario(usuario=None):
    """Sucursales activas y, al editar, la asignada aunque esté inactiva."""
    sucursales = Sucursal.query.filter_by(activa=True).order_by(Sucursal.nombre).all()
    if usuario and usuario.sucursal and usuario.sucursal not in sucursales:
        sucursales.append(usuario.sucursal)
    return sucursales


def _sucursal_valida(sucursal_id, usuario=None):
    if not sucursal_id:
        return None
    sucursal = db.session.get(Sucursal, sucursal_id)
    if not sucursal:
        return None
    if not sucursal.activa and not (usuario and usuario.sucursal_id == sucursal.id):
        return None
    return sucursal


def _valores_usuario(usuario=None):
    if request.method == "POST":
        return {
            "username": request.form.get("username", "").strip(),
            "rol": request.form.get("rol", ""),
            "sucursal_id": request.form.get("sucursal_id", type=int),
        }
    return {
        "username": usuario.username if usuario else "",
        "rol": usuario.rol if usuario else "cajero",
        "sucursal_id": usuario.sucursal_id if usuario else None,
    }


def _guardar_usuario(usuario=None):
    """Crea o actualiza un usuario. Devuelve True si se guardó."""
    valores = _valores_usuario(usuario)
    password = request.form.get("password", "")
    confirmacion = request.form.get("confirmacion", "")
    errores = []

    if not valores["username"]:
        errores.append("El nombre de usuario es obligatorio.")
    elif len(valores["username"]) > 80:
        errores.append("El nombre de usuario no puede superar 80 caracteres.")
    else:
        existente = Usuario.query.filter(
            db.func.lower(Usuario.username) == valores["username"].lower(),
            Usuario.id != (usuario.id if usuario else 0),
        ).first()
        if existente:
            errores.append("El nombre de usuario ya está en uso.")

    # Un administrador no puede quitarse a sí mismo el rol.
    if usuario and usuario.id == current_user.id:
        valores["rol"] = usuario.rol

    if valores["rol"] not in ROLES:
        errores.append("Seleccione un rol válido.")

    sucursal = _sucursal_valida(valores["sucursal_id"], usuario)
    if sucursal is None:
        errores.append("Seleccione una sucursal activa.")

    if not usuario or password:
        if len(password) < 6:
            errores.append("La contraseña debe tener al menos 6 caracteres.")
        if password != confirmacion:
            errores.append("Las contraseñas no coinciden.")

    if errores:
        flash(" ".join(errores), "danger")
        return False

    if usuario is None:
        usuario = Usuario()
        db.session.add(usuario)
    usuario.username = valores["username"]
    usuario.rol = valores["rol"]
    usuario.sucursal = sucursal
    if password:
        usuario.set_password(password)
    db.session.commit()
    return True


def _valores_sucursal(sucursal=None):
    if request.method == "POST":
        return {
            "nombre": request.form.get("nombre", "").strip(),
            "direccion": request.form.get("direccion", "").strip(),
            "telefono": request.form.get("telefono", "").strip(),
        }
    return {
        "nombre": sucursal.nombre if sucursal else "",
        "direccion": (sucursal.direccion or "") if sucursal else "",
        "telefono": (sucursal.telefono or "") if sucursal else "",
    }


def _guardar_sucursal(sucursal=None):
    valores = _valores_sucursal(sucursal)
    errores = []

    if not valores["nombre"]:
        errores.append("El nombre de la sucursal es obligatorio.")
    elif len(valores["nombre"]) > 80:
        errores.append("El nombre no puede superar 80 caracteres.")
    else:
        existente = Sucursal.query.filter(
            db.func.lower(Sucursal.nombre) == valores["nombre"].lower(),
            Sucursal.id != (sucursal.id if sucursal else 0),
        ).first()
        if existente:
            errores.append("Ya existe una sucursal con ese nombre.")

    if len(valores["direccion"]) > 200:
        errores.append("La dirección no puede superar 200 caracteres.")
    if len(valores["telefono"]) > 30:
        errores.append("El teléfono no puede superar 30 caracteres.")

    if errores:
        flash(" ".join(errores), "danger")
        return False

    if sucursal is None:
        sucursal = Sucursal()
        db.session.add(sucursal)
    sucursal.nombre = valores["nombre"]
    sucursal.direccion = valores["direccion"] or None
    sucursal.telefono = valores["telefono"] or None
    db.session.commit()
    return True


@bp.route("/")
@admin_required
def panel():
    sucursales = Sucursal.query.order_by(Sucursal.activa.desc(), Sucursal.nombre).all()
    resumen = []
    for sucursal in sucursales:
        resumen.append({
            "sucursal": sucursal,
            "usuarios": len(sucursal.usuarios),
            "productos": sum(1 for p in sucursal.productos if p.activo),
        })

    totales = {
        "usuarios": Usuario.query.count(),
        "sucursales": len(sucursales),
        "activas": sum(1 for s in sucursales if s.activa),
        "productos": Producto.query.filter_by(activo=True).count(),
        "movimientos": Movimiento.query.count(),
    }
    return render_template("admin/panel.html", totales=totales, resumen=resumen)


@bp.route("/usuarios")
@admin_required
def usuarios():
    return render_template(
        "admin/usuarios.html",
        usuarios=Usuario.query.order_by(Usuario.username).all(),
    )


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_required
def usuario_nuevo():
    if request.method == "POST" and _guardar_usuario():
        flash("Usuario «%s» registrado correctamente." % request.form.get("username", "").strip(),
              "success")
        return redirect(url_for("admin.usuarios"))
    return render_template(
        "admin/usuario_form.html",
        usuario=None,
        valores=_valores_usuario(),
        roles=ROLES,
        sucursales=_sucursales_formulario(),
    )


@bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def usuario_editar(id):
    usuario = db.get_or_404(Usuario, id)
    if request.method == "POST" and _guardar_usuario(usuario):
        flash("Usuario «%s» actualizado." % usuario.username, "success")
        return redirect(url_for("admin.usuarios"))
    return render_template(
        "admin/usuario_form.html",
        usuario=usuario,
        valores=_valores_usuario(usuario),
        roles=ROLES,
        sucursales=_sucursales_formulario(usuario),
    )


@bp.route("/sucursales")
@admin_required
def sucursales():
    return render_template(
        "admin/sucursales.html",
        sucursales=Sucursal.query.order_by(Sucursal.activa.desc(), Sucursal.nombre).all(),
    )


@bp.route("/sucursales/nueva", methods=["GET", "POST"])
@admin_required
def sucursal_nueva():
    if request.method == "POST" and _guardar_sucursal():
        flash("Sucursal «%s» creada correctamente." % request.form.get("nombre", "").strip(),
              "success")
        return redirect(url_for("admin.sucursales"))
    return render_template(
        "admin/sucursal_form.html",
        sucursal=None,
        valores=_valores_sucursal(),
    )


@bp.route("/sucursales/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def sucursal_editar(id):
    sucursal = db.get_or_404(Sucursal, id)
    if request.method == "POST" and _guardar_sucursal(sucursal):
        flash("Sucursal «%s» actualizada." % sucursal.nombre, "success")
        return redirect(url_for("admin.sucursales"))
    return render_template(
        "admin/sucursal_form.html",
        sucursal=sucursal,
        valores=_valores_sucursal(sucursal),
    )


@bp.route("/sucursales/<int:id>/estado", methods=["POST"])
@admin_required
def sucursal_estado(id):
    sucursal = db.get_or_404(Sucursal, id)
    if sucursal.activa:
        if sucursal.id == session.get(CLAVE_SESION):
            flash("No puede desactivar la sucursal activa en este momento.", "warning")
        elif sucursal.productos:
            flash("No se puede desactivar: la sucursal tiene productos asociados.", "danger")
        elif sucursal.usuarios:
            flash("No se puede desactivar: la sucursal tiene usuarios asignados.", "danger")
        else:
            sucursal.activa = False
            db.session.commit()
            flash("Sucursal «%s» desactivada." % sucursal.nombre, "success")
    else:
        sucursal.activa = True
        db.session.commit()
        flash("Sucursal «%s» activada." % sucursal.nombre, "success")
    return redirect(url_for("admin.sucursales"))
