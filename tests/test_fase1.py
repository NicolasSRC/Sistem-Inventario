from datetime import date, timedelta

import pytest

from app import db
from app.models import Categoria, Lote, Movimiento, Producto, Proveedor, Sucursal, Usuario


def test_datos_base(app):
    with app.app_context():
        assert Sucursal.query.count() == 1
        principal = Sucursal.query.filter_by(nombre="Principal").first()
        assert principal is not None

        admin = Usuario.query.filter_by(username="admin").first()
        cliente = Usuario.query.filter_by(username="cliente").first()
        assert admin.rol == "tendero"
        assert cliente.rol == "cajero"
        assert admin.es_admin is True
        assert cliente.es_admin is False
        assert admin.sucursal_id == principal.id


def test_proveedor_producto_y_lote(app):
    with app.app_context():
        proveedor = Proveedor(
            nombre="Distribuidora La 14",
            nit="900123456",
            contacto="Laura Pérez",
            telefono="3001234567",
            lead_time_dias=5,
        )
        categoria = Categoria.query.first()
        producto = Producto(
            nombre="Leche entera 1 L",
            sku="LAC-001",
            codigo_barras="7700000000001",
            precio=3500,
            precio_compra=2500,
            cantidad=10,
            stock_minimo=5,
            dias_alerta_vencimiento=15,
            categoria=categoria,
            proveedor=proveedor,
        )
        lote = Lote(
            producto=producto,
            codigo="L-001",
            fecha_vencimiento=date.today() + timedelta(days=10),
            cantidad_inicial=10,
            cantidad_actual=10,
            costo_unitario=2500,
        )
        db.session.add_all([proveedor, producto, lote])
        db.session.commit()

        assert producto.proveedor.nombre == "Distribuidora La 14"
        assert producto.categoria.nombre == categoria.nombre
        assert producto.margen == pytest.approx(28.5714, rel=1e-3)
        assert lote.por_vencer is True
        assert lote.vencido is False
        assert lote.dias_para_vencer == 10


def test_movimiento_con_trazabilidad(app):
    with app.app_context():
        admin = Usuario.query.filter_by(username="admin").first()
        producto = Producto(nombre="Producto de prueba", precio=1000, precio_compra=700, cantidad=10)
        db.session.add(producto)
        db.session.commit()

        movimiento = Movimiento(
            producto=producto,
            usuario_id=admin.id,
            tipo="entrada",
            motivo="compra",
            cantidad=5,
            costo_unitario=700,
            impacto=3500,
            stock_anterior=10,
            stock_nuevo=15,
            delta=5,
        )
        db.session.add(movimiento)
        db.session.commit()

        assert movimiento.efecto == 5
        assert movimiento.stock_anterior == 10
        assert movimiento.stock_nuevo == 15
        assert movimiento.usuario.username == "admin"


def test_movimiento_salida_y_ajuste(app):
    with app.app_context():
        producto = Producto(nombre="Producto 2", precio=2000, precio_compra=1200, cantidad=20)
        db.session.add(producto)
        db.session.commit()

        salida = Movimiento(producto_id=producto.id, tipo="salida", cantidad=3)
        ajuste = Movimiento(producto_id=producto.id, tipo="ajuste", cantidad=0, delta=-2)
        assert salida.efecto == -3
        assert ajuste.efecto == -2


def test_cajero_no_accede_a_categorias(cajero_client):
    respuesta = cajero_client.get("/categorias/", follow_redirects=True)
    assert respuesta.status_code == 200
    assert "Acción permitida solo para administradores" in respuesta.get_data(as_text=True)


def test_tendero_accede_a_categorias(admin_client):
    respuesta = admin_client.get("/categorias/")
    assert respuesta.status_code == 200
