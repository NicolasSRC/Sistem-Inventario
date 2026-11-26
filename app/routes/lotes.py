from flask import Blueprint, render_template, request

from ..models import Lote, Producto
from ..services.sucursales import filtrar
from ..utils import admin_required

bp = Blueprint("lotes", __name__, url_prefix="/lotes")

ESTADOS = ("vencido", "por_vencer", "vigente", "sin_fecha")


def _clasificar(lote):
    if lote.vencido:
        return "vencido"
    if lote.por_vencer:
        return "por_vencer"
    if lote.fecha_vencimiento:
        return "vigente"
    return "sin_fecha"


def _lotes_activos():
    return (filtrar(Lote.query, Lote).join(Producto)
            .filter(Producto.activo.is_(True), Lote.cantidad_actual > 0)
            .order_by(Lote.fecha_vencimiento.is_(None), Lote.fecha_vencimiento, Lote.id)
            .all())


@bp.route("/")
@admin_required
def lista():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "todos")

    todos = _lotes_activos()
    resumen = {clave: 0 for clave in ESTADOS}
    for lote in todos:
        resumen[_clasificar(lote)] += 1

    lotes = todos
    if q:
        texto = q.lower()
        lotes = [l for l in lotes
                 if texto in (l.producto.nombre or "").lower()
                 or texto in (l.codigo or "").lower()
                 or texto in (l.producto.sku or "").lower()]
    if estado in ESTADOS:
        lotes = [l for l in lotes if _clasificar(l) == estado]

    return render_template("lotes/lista.html", lotes=lotes, q=q, estado=estado,
                           resumen=resumen, estados=ESTADOS)
