"""Rotación de inventario y sugerencia de pedidos.

La rotación se calcula con las salidas reales (ventas) del período elegido.
La sugerencia de pedido cubre el consumo durante el tiempo de entrega del
proveedor más unos días de stock de seguridad, sin bajar del stock mínimo.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil

from ..models import Movimiento, Producto

PERIODOS = (7, 30, 90)
DIAS_SEGURIDAD = 7

ORDENES = {
    "mayor": "Mayor rotación",
    "menor": "Menor rotación",
    "reposicion": "Necesitan reposición",
}

ETIQUETAS_ROTACION = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
    "sin": "Sin rotación",
}


def _clasificar(venta_diaria):
    """Clasifica la rotación según el promedio de unidades vendidas por día."""
    if venta_diaria <= 0:
        return "sin"
    if venta_diaria >= 1:
        return "alta"
    if venta_diaria >= 0.2:
        return "media"
    return "baja"


def calcular_rotacion(periodo=30, sucursal_id=None):
    """Calcula los indicadores de rotación de los productos activos.

    Si se indica `sucursal_id`, solo se consideran los productos y las salidas
    de esa sucursal.
    """
    periodo = periodo if periodo in PERIODOS else 30
    desde = datetime.now() - timedelta(days=periodo)

    # Las salidas pueden generar varios movimientos para una misma venta (FEFO).
    consulta_salidas = (Movimiento.query.join(Producto)
                        .filter(Movimiento.tipo == "salida",
                                Movimiento.fecha >= desde,
                                Producto.activo.is_(True)))
    consulta_productos = Producto.query.filter_by(activo=True)
    if sucursal_id:
        consulta_salidas = consulta_salidas.filter(Movimiento.sucursal_id == sucursal_id)
        consulta_productos = consulta_productos.filter(Producto.sucursal_id == sucursal_id)

    salidas = consulta_salidas.all()

    acumulado = defaultdict(lambda: {"unidades": 0, "movimientos": 0, "dias": set()})
    for movimiento in salidas:
        datos = acumulado[movimiento.producto_id]
        datos["unidades"] += movimiento.cantidad or 0
        datos["movimientos"] += 1
        datos["dias"].add(movimiento.fecha.date())

    filas = []
    for producto in consulta_productos.order_by(Producto.nombre):
        datos = acumulado.get(producto.id, {"unidades": 0, "movimientos": 0, "dias": set()})
        unidades = datos["unidades"]
        venta_diaria = unidades / periodo
        stock = producto.cantidad or 0
        lead_time = producto.proveedor.lead_time_dias if producto.proveedor else 0

        stock_seguridad = ceil(venta_diaria * DIAS_SEGURIDAD)
        consumo_entrega = ceil(venta_diaria * lead_time)
        punto_pedido = max(producto.stock_minimo or 0, consumo_entrega + stock_seguridad)
        sugerido = max(0, punto_pedido - stock)
        rotacion = _clasificar(venta_diaria)

        filas.append({
            "producto": producto,
            "unidades": unidades,
            "movimientos": datos["movimientos"],
            "frecuencia": len(datos["dias"]),
            "venta_diaria": round(venta_diaria, 2),
            "dias_inventario": round(stock / venta_diaria, 1) if venta_diaria else None,
            "rotacion": rotacion,
            "etiqueta_rotacion": ETIQUETAS_ROTACION[rotacion],
            "lead_time": lead_time,
            "stock_seguridad": stock_seguridad,
            "consumo_entrega": consumo_entrega,
            "punto_pedido": punto_pedido,
            "sugerido": sugerido,
            "reponer": sugerido > 0,
        })

    resumen = {
        "productos": len(filas),
        "con_rotacion": sum(1 for f in filas if f["unidades"] > 0),
        "sin_rotacion": sum(1 for f in filas if f["unidades"] == 0),
        "reponer": sum(1 for f in filas if f["reponer"]),
        "unidades_sugeridas": sum(f["sugerido"] for f in filas),
    }
    return {"periodo": periodo, "filas": filas, "resumen": resumen}


def _ordenar(filas, orden):
    if orden == "menor":
        return sorted(filas, key=lambda f: (f["unidades"], f["frecuencia"], f["producto"].nombre))
    if orden == "reposicion":
        return sorted(filas, key=lambda f: (-f["sugerido"], -f["unidades"], f["producto"].nombre))
    return sorted(filas, key=lambda f: (-f["unidades"], -f["frecuencia"], f["producto"].nombre))


def obtener_rotacion(periodo=30, q="", categoria_id=None, solo_reponer=False, orden="mayor",
                     sucursal_id=None):
    """Devuelve el reporte filtrado y ordenado listo para la vista o el CSV."""
    if orden not in ORDENES:
        orden = "mayor"

    resultado = calcular_rotacion(periodo, sucursal_id=sucursal_id)
    filas = resultado["filas"]

    if q:
        texto = q.lower()
        filas = [f for f in filas
                 if texto in f["producto"].nombre.lower()
                 or texto in (f["producto"].sku or "").lower()
                 or texto in (f["producto"].codigo_barras or "").lower()]
    if categoria_id:
        filas = [f for f in filas if f["producto"].categoria_id == categoria_id]
    if solo_reponer:
        filas = [f for f in filas if f["reponer"]]

    resultado["filas"] = _ordenar(filas, orden)
    resultado["orden"] = orden
    resultado["resumen"]["mostrados"] = len(filas)
    return resultado
