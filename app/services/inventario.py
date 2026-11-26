"""Lógica de negocio de inventario.

Todas las variaciones de stock deben pasar por estos servicios para que el
historial de movimientos quede completo y consistente.
"""
from datetime import date, datetime

from .. import db
from ..models import Lote, Movimiento

MOTIVOS_MERMA = ("vencimiento", "dano", "robo", "devolucion", "otro")
MOTIVOS_AJUSTE = ("diferencia_conteo", "otro")


class InventarioError(ValueError):
    """Error de validación de una operación de inventario."""


def _stock(producto):
    return producto.cantidad or 0


def _commit():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _fecha_vencimiento(valor):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise InventarioError("La fecha de vencimiento no es válida (use AAAA-MM-DD).")


def _resolver_lote(producto, cantidad, costo_unitario, lote, lote_codigo, fecha_vencimiento):
    """Devuelve el lote que recibirá la entrada, creándolo si hace falta."""
    codigo = (lote_codigo or "").strip()
    fecha = _fecha_vencimiento(fecha_vencimiento)

    if lote is not None:
        lote.cantidad_inicial = (lote.cantidad_inicial or 0) + cantidad
        lote.cantidad_actual = (lote.cantidad_actual or 0) + cantidad
        return lote

    if not codigo and not fecha:
        return None
    if not codigo or not fecha:
        raise InventarioError("Para registrar un lote indique código y fecha de vencimiento.")
    if Lote.query.filter_by(producto_id=producto.id, codigo=codigo).first():
        raise InventarioError("Ya existe un lote con ese código para este producto.")

    return Lote(
        producto=producto,
        sucursal_id=producto.sucursal_id,
        codigo=codigo,
        fecha_vencimiento=fecha,
        cantidad_inicial=cantidad,
        cantidad_actual=cantidad,
        costo_unitario=round(costo_unitario, 2),
    )


def _movimiento(producto, tipo, motivo, cantidad, delta, costo, stock_anterior,
                stock_nuevo, observacion, usuario, lote):
    return Movimiento(
        producto=producto,
        usuario_id=usuario.id if usuario else None,
        lote=lote,
        sucursal_id=producto.sucursal_id,
        tipo=tipo,
        motivo=motivo,
        cantidad=cantidad,
        costo_unitario=round(costo, 2),
        impacto=round(cantidad * costo, 2),
        stock_anterior=stock_anterior,
        stock_nuevo=stock_nuevo,
        delta=delta,
        observacion=(observacion or "").strip(),
    )


def _lotes_fefo(producto):
    lotes = Lote.query.filter(
        Lote.producto_id == producto.id,
        Lote.cantidad_actual > 0,
    ).all()
    # FEFO: primero el vencimiento más cercano; los lotes sin fecha van al final.
    lotes.sort(key=lambda l: (l.fecha_vencimiento is None,
                              l.fecha_vencimiento or date.max, l.id))
    return lotes


def _descontar(producto, cantidad, tipo, motivo, observacion, usuario):
    """Descuenta stock consumiendo lotes FEFO y el resto del stock agregado."""
    stock_anterior = _stock(producto)
    restante = cantidad
    stock_actual = stock_anterior
    movimientos = []

    for lote in _lotes_fefo(producto):
        if restante <= 0:
            break
        tomar = min(lote.cantidad_actual, restante)
        if tomar <= 0:
            continue
        lote.cantidad_actual -= tomar
        stock_actual -= tomar
        movimientos.append(_movimiento(
            producto, tipo, motivo, tomar, -tomar,
            lote.costo_unitario or producto.precio_compra or 0,
            stock_actual + tomar, stock_actual, observacion, usuario, lote,
        ))
        restante -= tomar

    if restante > 0:
        stock_actual -= restante
        movimientos.append(_movimiento(
            producto, tipo, motivo, restante, -restante,
            producto.precio_compra or 0,
            stock_actual + restante, stock_actual, observacion, usuario, None,
        ))

    producto.cantidad = stock_actual
    return movimientos


def _guardar_salida(producto, movimientos):
    db.session.add(producto)
    for movimiento in movimientos:
        db.session.add(movimiento)
    _commit()


def registrar_entrada(producto, cantidad, costo_unitario=None, proveedor=None,
                      actualizar_costo=True, observacion="", usuario=None,
                      motivo="compra", lote=None, lote_codigo=None,
                      fecha_vencimiento=None):
    """Registra una entrada de stock y actualiza el costo promedio ponderado."""
    if cantidad is None or cantidad <= 0:
        raise InventarioError("La cantidad debe ser mayor a 0.")

    if costo_unitario is None or costo_unitario == "":
        costo_unitario = producto.precio_compra or 0
    try:
        costo_unitario = float(costo_unitario)
    except (TypeError, ValueError):
        raise InventarioError("El costo unitario no es válido.")
    if costo_unitario < 0:
        raise InventarioError("El costo unitario no puede ser negativo.")

    lote = _resolver_lote(producto, cantidad, costo_unitario, lote, lote_codigo,
                          fecha_vencimiento)

    stock_anterior = _stock(producto)
    costo_anterior = producto.precio_compra or 0
    producto.cantidad = stock_anterior + cantidad

    if actualizar_costo and producto.cantidad > 0:
        valor_anterior = stock_anterior * costo_anterior
        valor_entrada = cantidad * costo_unitario
        producto.precio_compra = round((valor_anterior + valor_entrada) / producto.cantidad, 2)

    if proveedor is not None:
        producto.proveedor = proveedor

    movimiento = _movimiento(
        producto, "entrada", motivo, cantidad, cantidad, costo_unitario,
        stock_anterior, producto.cantidad, observacion, usuario, lote,
    )
    db.session.add(producto)
    db.session.add(movimiento)
    if lote is not None:
        db.session.add(lote)
    _commit()
    return movimiento


def registrar_salida(producto, cantidad, motivo="venta", observacion="", usuario=None):
    """Registra una salida y consume los lotes con criterio FEFO.

    Devuelve la lista de movimientos generados. Si la salida supera el stock
    disponible en lotes, el resto se descuenta del stock agregado del producto.
    """
    if cantidad is None or cantidad <= 0:
        raise InventarioError("La cantidad debe ser mayor a 0.")

    stock_anterior = _stock(producto)
    if cantidad > stock_anterior:
        raise InventarioError(
            "Stock insuficiente: disponible %d, solicitado %d." % (stock_anterior, cantidad)
        )

    movimientos = _descontar(producto, cantidad, "salida", motivo, observacion, usuario)
    _guardar_salida(producto, movimientos)
    return movimientos


def registrar_ajuste(producto, delta, motivo=None, observacion="", usuario=None,
                     tipo="ajuste"):
    """Registra un ajuste positivo/negativo o una merma.

    `delta` es la variación firmada del stock. En una merma debe ser negativa.
    Devuelve la lista de movimientos generados.
    """
    if tipo not in ("ajuste", "merma"):
        raise InventarioError("El tipo debe ser ajuste o merma.")
    try:
        delta = int(delta)
    except (TypeError, ValueError):
        raise InventarioError("La cantidad del ajuste no es válida.")
    if delta == 0:
        raise InventarioError("La cantidad del ajuste debe ser diferente de 0.")

    if tipo == "merma":
        motivo = motivo or "vencimiento"
        if motivo not in MOTIVOS_MERMA:
            raise InventarioError("El motivo de la merma no es válido.")
        if delta > 0:
            raise InventarioError("Una merma debe disminuir el stock.")
    else:
        motivo = motivo or "diferencia_conteo"
        if motivo not in MOTIVOS_AJUSTE:
            raise InventarioError("El motivo del ajuste no es válido.")

    stock_anterior = _stock(producto)
    stock_nuevo = stock_anterior + delta
    if stock_nuevo < 0:
        raise InventarioError(
            "El ajuste dejaría el stock en negativo: disponible %d, variación %d."
            % (stock_anterior, delta)
        )

    if delta > 0:
        producto.cantidad = stock_nuevo
        movimiento = _movimiento(
            producto, "ajuste", motivo, delta, delta,
            producto.precio_compra or 0, stock_anterior, stock_nuevo,
            observacion, usuario, None,
        )
        db.session.add(producto)
        db.session.add(movimiento)
        _commit()
        return [movimiento]

    movimientos = _descontar(producto, abs(delta), tipo, motivo, observacion, usuario)
    _guardar_salida(producto, movimientos)
    return movimientos
