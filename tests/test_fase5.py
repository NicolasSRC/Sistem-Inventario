from datetime import date, timedelta

import pytest

from app import db
from app.models import Categoria, Lote, Movimiento, Producto
from app.services.inventario import InventarioError, registrar_ajuste


def _producto(**cambios):
    datos = dict(nombre="Producto ajuste", precio=2000, precio_compra=1000, cantidad=10)
    datos.update(cambios)
    return Producto(**datos)


def _crear_producto(app, client, nombre, sku, cantidad="10"):
    with app.app_context():
        categoria_id = Categoria.query.first().id
    return client.post(
        "/productos/nuevo",
        data={
            "nombre": nombre,
            "sku": sku,
            "precio": "2500",
            "precio_compra": "1000",
            "cantidad": cantidad,
            "stock_minimo": "2",
            "dias_alerta_vencimiento": "15",
            "categoria_id": str(categoria_id),
        },
        follow_redirects=True,
    )


def test_ajuste_positivo_aumenta_stock(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        movimientos = registrar_ajuste(producto, 5, motivo="diferencia_conteo")

        assert producto.cantidad == 15
        assert len(movimientos) == 1
        movimiento = movimientos[0]
        assert movimiento.tipo == "ajuste"
        assert movimiento.motivo == "diferencia_conteo"
        assert movimiento.cantidad == 5
        assert movimiento.delta == 5
        assert movimiento.efecto == 5
        assert movimiento.stock_anterior == 10
        assert movimiento.stock_nuevo == 15
        assert movimiento.impacto == 5000


def test_merma_disminuye_stock_y_calcula_impacto(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        movimientos = registrar_ajuste(
            producto, -3, motivo="dano", observacion="Empaque roto", tipo="merma"
        )

        assert producto.cantidad == 7
        assert len(movimientos) == 1
        movimiento = movimientos[0]
        assert movimiento.tipo == "merma"
        assert movimiento.motivo == "dano"
        assert movimiento.cantidad == 3
        assert movimiento.delta == -3
        assert movimiento.efecto == -3
        assert movimiento.impacto == 3000
        assert movimiento.observacion == "Empaque roto"


def test_merma_consume_lotes_fefo(app):
    with app.app_context():
        producto = _producto(cantidad=10)
        db.session.add(producto)
        db.session.flush()
        cercano = Lote(producto=producto, codigo="L-CERCA", fecha_vencimiento=date.today() + timedelta(days=4),
                       cantidad_inicial=4, cantidad_actual=4, costo_unitario=1000)
        lejano = Lote(producto=producto, codigo="L-LEJOS", fecha_vencimiento=date.today() + timedelta(days=60),
                      cantidad_inicial=3, cantidad_actual=3, costo_unitario=1000)
        db.session.add_all([cercano, lejano])
        db.session.commit()

        movimientos = registrar_ajuste(producto, -5, motivo="vencimiento", tipo="merma")

        assert producto.cantidad == 5
        assert cercano.cantidad_actual == 0
        assert lejano.cantidad_actual == 2
        assert [m.cantidad for m in movimientos] == [4, 1]
        assert movimientos[0].lote.codigo == "L-CERCA"
        assert movimientos[1].lote.codigo == "L-LEJOS"
        assert all(m.tipo == "merma" for m in movimientos)


def test_ajuste_negativo_consume_lotes(app):
    with app.app_context():
        producto = _producto(cantidad=8)
        db.session.add(producto)
        db.session.flush()
        lote = Lote(producto=producto, codigo="L-001", fecha_vencimiento=date.today() + timedelta(days=10),
                    cantidad_inicial=3, cantidad_actual=3, costo_unitario=1000)
        db.session.add(lote)
        db.session.commit()

        movimientos = registrar_ajuste(producto, -4, motivo="diferencia_conteo")

        assert producto.cantidad == 4
        assert lote.cantidad_actual == 0
        assert len(movimientos) == 2
        assert movimientos[0].tipo == "ajuste"
        assert movimientos[0].lote.codigo == "L-001"
        assert movimientos[1].lote_id is None
        assert movimientos[1].cantidad == 1


def test_validaciones_de_ajustes_y_mermas(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        with pytest.raises(InventarioError):
            registrar_ajuste(producto, 0)
        with pytest.raises(InventarioError):
            registrar_ajuste(producto, 5, tipo="merma", motivo="vencimiento")
        with pytest.raises(InventarioError):
            registrar_ajuste(producto, -100, tipo="ajuste")
        with pytest.raises(InventarioError):
            registrar_ajuste(producto, 1, tipo="ajuste", motivo="vencimiento")
        with pytest.raises(InventarioError):
            registrar_ajuste(producto, 1, tipo="otro")

        assert producto.cantidad == 10
        assert Movimiento.query.count() == 0


def test_ruta_merma_y_ajuste(app, admin_client):
    _crear_producto(app, admin_client, "Producto merma ruta", "MER-001")

    with app.app_context():
        producto_id = Producto.query.filter_by(sku="MER-001").one().id

    respuesta = admin_client.post(
        "/movimientos/ajuste",
        data={
            "producto_id": str(producto_id),
            "tipo": "merma",
            "motivo": "dano",
            "cantidad": "3",
            "observacion": "Producto dañado en bodega",
        },
        follow_redirects=True,
    )
    assert "Merma registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        producto = db.session.get(Producto, producto_id)
        assert producto.cantidad == 7
        movimiento = Movimiento.query.filter_by(producto_id=producto_id).order_by(Movimiento.id.desc()).first()
        assert movimiento.tipo == "merma"
        assert movimiento.motivo == "dano"
        assert movimiento.delta == -3

    respuesta = admin_client.post(
        "/movimientos/ajuste",
        data={
            "producto_id": str(producto_id),
            "tipo": "ajuste",
            "direccion": "aumentar",
            "motivo": "diferencia_conteo",
            "cantidad": "2",
            "observacion": "Conteo físico",
        },
        follow_redirects=True,
    )
    assert "Ajuste registrado" in respuesta.get_data(as_text=True)

    with app.app_context():
        producto = db.session.get(Producto, producto_id)
        assert producto.cantidad == 9
        movimiento = Movimiento.query.filter_by(producto_id=producto_id).order_by(Movimiento.id.desc()).first()
        assert movimiento.tipo == "ajuste"
        assert movimiento.delta == 2


def test_ruta_merma_insuficiente_no_modifica_stock(app, admin_client):
    _crear_producto(app, admin_client, "Producto merma inválida", "MER-002", cantidad="4")

    with app.app_context():
        producto_id = Producto.query.filter_by(sku="MER-002").one().id

    respuesta = admin_client.post(
        "/movimientos/ajuste",
        data={
            "producto_id": str(producto_id),
            "tipo": "merma",
            "motivo": "vencimiento",
            "cantidad": "10",
        },
        follow_redirects=True,
    )
    assert "dejaría el stock en negativo" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Producto, producto_id).cantidad == 4


def test_historial_filtra_ajustes_y_mermas(app, admin_client):
    _crear_producto(app, admin_client, "Producto solo merma", "FIL-001")
    _crear_producto(app, admin_client, "Producto solo ajuste", "FIL-002")

    with app.app_context():
        merma_id = Producto.query.filter_by(sku="FIL-001").one().id
        ajuste_id = Producto.query.filter_by(sku="FIL-002").one().id

    admin_client.post("/movimientos/ajuste", data={
        "producto_id": str(merma_id), "tipo": "merma", "motivo": "robo", "cantidad": "1",
    }, follow_redirects=True)
    admin_client.post("/movimientos/ajuste", data={
        "producto_id": str(ajuste_id), "tipo": "ajuste", "direccion": "aumentar",
        "motivo": "diferencia_conteo", "cantidad": "2",
    }, follow_redirects=True)

    mermas = admin_client.get("/movimientos/?tipo=merma").get_data(as_text=True)
    assert "Producto solo merma" in mermas
    assert "Producto solo ajuste" not in mermas

    ajustes = admin_client.get("/movimientos/?tipo=ajuste").get_data(as_text=True)
    assert "Producto solo ajuste" in ajustes
    assert "Producto solo merma" not in ajustes


def test_reporte_mermas_y_dashboard(app, admin_client):
    _crear_producto(app, admin_client, "Producto reporte merma", "REP-MER")

    with app.app_context():
        producto_id = Producto.query.filter_by(sku="REP-MER").one().id

    admin_client.post("/movimientos/ajuste", data={
        "producto_id": str(producto_id), "tipo": "merma", "motivo": "dano", "cantidad": "2",
    }, follow_redirects=True)

    csv = admin_client.get("/reportes/mermas.csv").get_data(as_text=True)
    assert "Producto reporte merma" in csv
    assert "dano" in csv

    dashboard = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Mermas del mes" in dashboard


def test_cajero_no_accede_a_ajustes(cajero_client):
    respuesta = cajero_client.get("/movimientos/ajuste", follow_redirects=True)
    assert "Acción permitida solo para administradores" in respuesta.get_data(as_text=True)
