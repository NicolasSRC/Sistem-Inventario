from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import db
from ..models import Lote, Movimiento, Producto

bp = Blueprint("dashboard", __name__)

PERIODOS = (7, 30)


@bp.route("/dashboard")
@login_required
def index():
    periodo = request.args.get("periodo", type=int) or 7
    if periodo not in PERIODOS:
        periodo = 7

    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    desde = hoy - timedelta(days=periodo - 1)

    activos = Producto.query.filter_by(activo=True)
    total = activos.count()
    unidades = db.session.query(func.coalesce(func.sum(Producto.cantidad), 0)).filter(Producto.activo.is_(True)).scalar()
    valor = db.session.query(func.coalesce(func.sum(Producto.precio * Producto.cantidad), 0)).filter(Producto.activo.is_(True)).scalar()
    alertas = activos.filter(Producto.cantidad <= Producto.stock_minimo).count()
    ultimos = Movimiento.query.order_by(Movimiento.fecha.desc()).limit(8).all()

    # Ventas del período (las salidas pueden generar varios movimientos por lote).
    ventas = (Movimiento.query.join(Producto)
              .filter(Movimiento.tipo == "salida", Movimiento.fecha >= desde)
              .all())
    dias = [desde.date() + timedelta(days=i) for i in range(periodo)]
    unidades_dia = {d: 0 for d in dias}
    ingresos_dia = {d: 0.0 for d in dias}
    por_producto = {}

    for movimiento in ventas:
        dia = movimiento.fecha.date()
        ingreso = movimiento.cantidad * (movimiento.producto.precio or 0)
        if dia in unidades_dia:
            unidades_dia[dia] += movimiento.cantidad
            ingresos_dia[dia] += ingreso
        datos = por_producto.setdefault(
            movimiento.producto_id,
            {"nombre": movimiento.producto.nombre, "unidades": 0, "ingresos": 0.0},
        )
        datos["unidades"] += movimiento.cantidad
        datos["ingresos"] += ingreso

    top_productos = sorted(por_producto.values(),
                           key=lambda x: (x["unidades"], x["ingresos"]), reverse=True)[:5]

    ventas_labels = [d.strftime("%d/%m") for d in dias]
    ventas_unidades = [unidades_dia[d] for d in dias]
    ventas_ingresos = [round(ingresos_dia[d], 2) for d in dias]

    ventas_hoy = unidades_dia.get(hoy.date(), 0)
    ingresos_hoy = ingresos_dia.get(hoy.date(), 0)
    movimientos_hoy = Movimiento.query.filter(Movimiento.fecha >= hoy).count()

    # Valor del inventario por categoría.
    categorias = {}
    for producto in activos.all():
        if (producto.cantidad or 0) <= 0:
            continue
        nombre = producto.categoria.nombre if producto.categoria else "Sin categoría"
        categorias[nombre] = categorias.get(nombre, 0) + (producto.precio or 0) * (producto.cantidad or 0)
    categorias_ordenadas = sorted(categorias.items(), key=lambda x: x[1], reverse=True)

    inicio_mes = hoy.replace(day=1)
    mermas_mes = Movimiento.query.filter(
        Movimiento.tipo == "merma", Movimiento.fecha >= inicio_mes
    ).count()
    impacto_mermas_mes = db.session.query(
        func.coalesce(func.sum(Movimiento.impacto), 0)
    ).filter(Movimiento.tipo == "merma", Movimiento.fecha >= inicio_mes).scalar()

    lotes_por_vencer = lotes_vencidos = 0
    proximos_lotes = []
    lotes_estado = {"Vencidos": 0, "Por vencer": 0, "Vigentes": 0, "Sin fecha": 0}
    if current_user.es_admin:
        lotes = (Lote.query.join(Producto)
                 .filter(Producto.activo.is_(True), Lote.cantidad_actual > 0)
                 .all())
        lotes_por_vencer = sum(1 for l in lotes if l.por_vencer)
        lotes_vencidos = sum(1 for l in lotes if l.vencido)
        proximos_lotes = sorted(
            (l for l in lotes if l.fecha_vencimiento and not l.vencido),
            key=lambda l: (l.fecha_vencimiento, l.id),
        )[:5]
        for lote in lotes:
            if lote.vencido:
                lotes_estado["Vencidos"] += 1
            elif lote.por_vencer:
                lotes_estado["Por vencer"] += 1
            elif lote.fecha_vencimiento:
                lotes_estado["Vigentes"] += 1
            else:
                lotes_estado["Sin fecha"] += 1

    return render_template(
        "dashboard.html",
        periodo=periodo,
        total=total,
        unidades=unidades,
        valor=valor,
        alertas=alertas,
        ultimos=ultimos,
        lotes_por_vencer=lotes_por_vencer,
        lotes_vencidos=lotes_vencidos,
        proximos_lotes=proximos_lotes,
        mermas_mes=mermas_mes,
        impacto_mermas_mes=impacto_mermas_mes,
        ventas_labels=ventas_labels,
        ventas_unidades=ventas_unidades,
        ventas_ingresos=ventas_ingresos,
        top_productos=top_productos,
        categorias_labels=[c[0] for c in categorias_ordenadas],
        categorias_valores=[round(c[1], 2) for c in categorias_ordenadas],
        lotes_estado_labels=list(lotes_estado.keys()),
        lotes_estado_valores=list(lotes_estado.values()),
        ventas_hoy=ventas_hoy,
        ingresos_hoy=ingresos_hoy,
        movimientos_hoy=movimientos_hoy,
    )
