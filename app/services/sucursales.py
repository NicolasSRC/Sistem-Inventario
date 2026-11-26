"""Resolución de la sucursal activa y filtros por sede.

El tendero puede cambiar de sucursal desde el menú lateral; el cajero siempre
opera sobre la sucursal que tiene asignada. Toda consulta de productos,
movimientos y lotes debe pasar por estas funciones para no mezclar stock.
"""
from flask import session
from flask_login import current_user

from .. import db
from ..models import Producto, Sucursal

CLAVE_SESION = "sucursal_id"


def sucursales_activas():
    return Sucursal.query.filter_by(activa=True).order_by(Sucursal.nombre).all()


def sucursal_actual():
    """Sucursal sobre la que opera el usuario autenticado."""
    if not current_user.is_authenticated:
        return None

    if current_user.es_admin:
        elegida = session.get(CLAVE_SESION)
        if elegida:
            sucursal = db.session.get(Sucursal, elegida)
            if sucursal and sucursal.activa:
                return sucursal

    if current_user.sucursal_id:
        asignada = db.session.get(Sucursal, current_user.sucursal_id)
        if asignada:
            return asignada

    activas = sucursales_activas()
    return activas[0] if activas else None


def establecer_sucursal(sucursal_id):
    """Guarda la sucursal elegida en la sesión del tendero.

    Devuelve la sucursal si es válida y está activa; de lo contrario, None.
    """
    if not sucursal_id:
        return None
    sucursal = db.session.get(Sucursal, sucursal_id)
    if not sucursal or not sucursal.activa:
        return None
    session[CLAVE_SESION] = sucursal.id
    return sucursal


def filtrar(query, modelo):
    """Aplica la sucursal activa a una consulta del modelo indicado."""
    sucursal = sucursal_actual()
    if sucursal is None:
        return query
    return query.filter(modelo.sucursal_id == sucursal.id)


def productos_query():
    return filtrar(Producto.query, Producto)


def producto_actual(producto_id):
    """Producto de la sucursal activa o None si pertenece a otra sede."""
    if not producto_id:
        return None
    return productos_query().filter(Producto.id == producto_id).first()
