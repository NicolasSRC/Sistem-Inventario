from datetime import date, timedelta

import pytest

from app import db
from app.models import Categoria, Lote, Movimiento, Producto
from app.services.inventario import InventarioError, registrar_entrada, registrar_salida


def _producto(**cambios):
    datos = dict(nombre="Producto con lote", precio=2000, precio_compra=1000, cantidad=0,
                 sucursal_id=1)  # Principal
    datos.update(cambios)
    return Producto(**datos)


def _fecha(dias):
    return date.today() + timedelta(days=dias)


def test_entrada_con_lote_crea_lote_y_movimiento(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        movimiento = registrar_entrada(
            producto, 10, costo_unitario=1200,
            lote_codigo="L-001", fecha_vencimiento=_fecha(30),
            observacion="Compra con lote",
        )

        lote = Lote.query.filter_by(producto_id=producto.id, codigo="L-001").one()
        assert producto.cantidad == 10
        assert lote.cantidad_inicial == 10
        assert lote.cantidad_actual == 10
        assert lote.costo_unitario == 1200
        assert lote.fecha_vencimiento == _fecha(30)
        assert movimiento.lote_id == lote.id
        assert movimiento.tipo == "entrada"
        assert movimiento.impacto == 12000


def test_entrada_con_lote_valida_codigo_fecha_y_duplicados(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        with pytest.raises(InventarioError):
            registrar_entrada(producto, 5, lote_codigo="SIN-FECHA")
        with pytest.raises(InventarioError):
            registrar_entrada(producto, 5, fecha_vencimiento=_fecha(10))
        with pytest.raises(InventarioError):
            registrar_entrada(producto, 5, lote_codigo="MAL", fecha_vencimiento="no-es-fecha")

        assert producto.cantidad == 0
        assert Lote.query.count() == 0

        registrar_entrada(producto, 5, lote_codigo="L-001", fecha_vencimiento=_fecha(10))
        with pytest.raises(InventarioError, match="Ya existe un lote"):
            registrar_entrada(producto, 5, lote_codigo="L-001", fecha_vencimiento=_fecha(20))

        assert producto.cantidad == 5
        assert Lote.query.count() == 1


def test_salida_fefo_consume_primero_el_vencimiento_mas_cercano(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        registrar_entrada(producto, 5, costo_unitario=1000,
                          lote_codigo="L-LEJOS", fecha_vencimiento=_fecha(40))
        registrar_entrada(producto, 5, costo_unitario=1000,
                          lote_codigo="L-CERCA", fecha_vencimiento=_fecha(5))

        movimientos = registrar_salida(producto, 7, observacion="Venta FEFO")

        assert producto.cantidad == 3
        assert Lote.query.filter_by(codigo="L-CERCA").one().cantidad_actual == 0
        assert Lote.query.filter_by(codigo="L-LEJOS").one().cantidad_actual == 3
        assert len(movimientos) == 2
        assert movimientos[0].lote.codigo == "L-CERCA"
        assert movimientos[0].cantidad == 5
        assert movimientos[0].stock_anterior == 10
        assert movimientos[0].stock_nuevo == 5
        assert movimientos[1].lote.codigo == "L-LEJOS"
        assert movimientos[1].cantidad == 2
        assert movimientos[1].stock_anterior == 5
        assert movimientos[1].stock_nuevo == 3


def test_salida_consume_lotes_y_descuenta_resto_agregado(app):
    with app.app_context():
        producto = _producto(cantidad=10)
        lote = Lote(producto=producto, sucursal_id=1, codigo="L-001", fecha_vencimiento=_fecha(10),
                    cantidad_inicial=3, cantidad_actual=3, costo_unitario=1000)
        db.session.add_all([producto, lote])
        db.session.commit()

        movimientos = registrar_salida(producto, 5)

        assert producto.cantidad == 5
        assert lote.cantidad_actual == 0
        assert [m.cantidad for m in movimientos] == [3, 2]
        assert movimientos[0].lote.codigo == "L-001"
        assert movimientos[1].lote_id is None


def test_salida_sin_lotes_mantiene_compatibilidad(app):
    with app.app_context():
        producto = _producto(cantidad=10)
        db.session.add(producto)
        db.session.commit()

        movimientos = registrar_salida(producto, 4)

        assert producto.cantidad == 6
        assert len(movimientos) == 1
        assert movimientos[0].lote_id is None
        assert movimientos[0].cantidad == 4


def test_ruta_entrada_registra_lote_y_dias_alerta(app, admin_client):
    with app.app_context():
        categoria = Categoria.query.first()
        categoria_id = categoria.id

    respuesta = admin_client.post(
        "/productos/nuevo",
        data={
            "nombre": "Leche con lote",
            "sku": "LOT-001",
            "precio": "3500",
            "precio_compra": "2500",
            "cantidad": "0",
            "stock_minimo": "2",
            "dias_alerta_vencimiento": "10",
            "categoria_id": str(categoria_id),
        },
        follow_redirects=True,
    )
    assert "Producto registrado correctamente" in respuesta.get_data(as_text=True)

    with app.app_context():
        producto = Producto.query.filter_by(sku="LOT-001").one()
        producto_id = producto.id
        assert producto.dias_alerta_vencimiento == 10

    vencimiento = _fecha(5).isoformat()
    respuesta = admin_client.post(
        "/movimientos/registrar",
        data={
            "producto_id": str(producto_id),
            "tipo": "entrada",
            "cantidad": "8",
            "costo_unitario": "2500",
            "actualizar_costo": "on",
            "lote_codigo": "L-RUTA-01",
            "fecha_vencimiento": vencimiento,
            "observacion": "Compra de leche",
        },
        follow_redirects=True,
    )
    texto = respuesta.get_data(as_text=True)
    assert "Entrada registrada" in texto
    assert "L-RUTA-01" in texto

    with app.app_context():
        producto = db.session.get(Producto, producto_id)
        lote = Lote.query.filter_by(producto_id=producto_id, codigo="L-RUTA-01").one()
        assert producto.cantidad == 8
        assert lote.cantidad_actual == 8
        movimiento = Movimiento.query.filter_by(producto_id=producto_id).order_by(Movimiento.id.desc()).first()
        assert movimiento.lote_id == lote.id

    listado = admin_client.get("/lotes/").get_data(as_text=True)
    assert "Leche con lote" in listado
    assert "L-RUTA-01" in listado

    por_vencer = admin_client.get("/lotes/?estado=por_vencer").get_data(as_text=True)
    assert "L-RUTA-01" in por_vencer

    historial = admin_client.get("/movimientos/").get_data(as_text=True)
    assert "L-RUTA-01" in historial

    dashboard = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Lotes por vencer" in dashboard
    assert "Leche con lote" in dashboard

    csv_lotes = admin_client.get("/reportes/lotes.csv").get_data(as_text=True)
    assert "L-RUTA-01" in csv_lotes
    assert "Por vencer" in csv_lotes


def test_lista_lotes_filtra_por_estado(app, admin_client):
    with app.app_context():
        producto = _producto(nombre="Producto filtros", cantidad=15)
        db.session.add(producto)
        db.session.flush()
        db.session.add_all([
            Lote(producto=producto, sucursal_id=1, codigo="VENCIDO", fecha_vencimiento=_fecha(-2),
                 cantidad_inicial=5, cantidad_actual=5, costo_unitario=1000),
            Lote(producto=producto, sucursal_id=1, codigo="PROXIMO", fecha_vencimiento=_fecha(5),
                 cantidad_inicial=5, cantidad_actual=5, costo_unitario=1000),
            Lote(producto=producto, sucursal_id=1, codigo="VIGENTE", fecha_vencimiento=_fecha(90),
                 cantidad_inicial=5, cantidad_actual=5, costo_unitario=1000),
        ])
        db.session.commit()

    texto = admin_client.get("/lotes/?estado=vencido").get_data(as_text=True)
    assert "VENCIDO" in texto
    assert "PROXIMO" not in texto
    assert "VIGENTE" not in texto

    texto = admin_client.get("/lotes/?estado=por_vencer").get_data(as_text=True)
    assert "PROXIMO" in texto
    assert "VENCIDO" not in texto

    texto = admin_client.get("/lotes/?estado=vigente").get_data(as_text=True)
    assert "VIGENTE" in texto
    assert "PROXIMO" not in texto


def test_cajero_no_accede_a_lotes(cajero_client):
    respuesta = cajero_client.get("/lotes/", follow_redirects=True)
    assert "Acción permitida solo para administradores" in respuesta.get_data(as_text=True)
