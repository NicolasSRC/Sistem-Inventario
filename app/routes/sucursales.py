"""Cambio de sucursal activa para el tendero."""
from flask import Blueprint, flash, redirect, request, url_for

from ..services.sucursales import establecer_sucursal
from ..utils import admin_required

bp = Blueprint("sucursales", __name__, url_prefix="/sucursales")


@bp.route("/cambiar", methods=["POST"])
@admin_required
def cambiar():
    sucursal = establecer_sucursal(request.form.get("sucursal_id", type=int))
    if sucursal is None:
        flash("La sucursal seleccionada no está disponible.", "warning")
    else:
        flash("Ahora opera en la sucursal «%s»." % sucursal.nombre, "success")
    return redirect(url_for("dashboard.index"))
