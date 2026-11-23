import pytest

from app import db
from app.models import Categoria, Movimiento, Producto, Usuario
from app.services.inventario import InventarioError, registrar_entrada, registrar_salida


def _producto(nombre="Producto", cantidad=10, precio_compra=1000, precio=2000):
    return Producto(nombre=nombre, precio=precio, precio_compra=precio_compra, cantidad=cantidad)


def test_entrada_actualiza_stock_y_costo_promedio(app):
    with app.app_context():
        usuario = Usuario.query.filter_by(username="admin").first()
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        movimiento = registrar_entrada(
            producto, 10, costo_unitario=2000, observacion="Compra", usuario=usuario
        )

        assert producto.cantidad == 20
        assert producto.precio_compra == 1500
        assert movimiento.tipo == "entrada"
        assert movimiento.motivo == "compra"
        assert movimiento.cantidad == 10
        assert movimiento.costo_unitario == 2000
        assert movimiento.impacto == 20000
        assert movimiento.stock_anterior == 10
        assert movimiento.stock_nuevo == 20
        assert movimiento.delta == 10
        assert movimiento.usuario_id == usuario.id


def test_entrada_sin_actualizar_costo(app):
    with app.app_context():
        producto = _producto(cantidad=5, precio_compra=1000)
        db.session.add(producto)
        db.session.commit()

        registrar_entrada(producto, 5, costo_unitario=3000, actualizar_costo=False)

        assert producto.cantidad == 10
        assert producto.precio_compra == 1000


def test_salida_valida_stock_y_calcula_impacto(app):
    with app.app_context():
        producto = _producto(cantidad=10, precio_compra=700)
        db.session.add(producto)
        db.session.commit()

        movimientos = registrar_salida(producto, 4, observacion="Venta")
        movimiento = movimientos[0]

        assert producto.cantidad == 6
        assert len(movimientos) == 1
        assert movimiento.tipo == "salida"
        assert movimiento.motivo == "venta"
        assert movimiento.impacto == 2800
        assert movimiento.stock_anterior == 10
        assert movimiento.stock_nuevo == 6
        assert movimiento.delta == -4

        with pytest.raises(InventarioError):
            registrar_salida(producto, 100)
        assert producto.cantidad == 6


def test_validaciones_de_inventario(app):
    with app.app_context():
        producto = _producto()
        db.session.add(producto)
        db.session.commit()

        with pytest.raises(InventarioError):
            registrar_entrada(producto, 0)
        with pytest.raises(InventarioError):
            registrar_entrada(producto, 1, costo_unitario=-1)
        with pytest.raises(InventarioError):
            registrar_salida(producto, 0)


def _crear_producto_por_ruta(client, **cambios):
    categoria = Categoria.query.first()
    datos = {
        "nombre": "Producto Fase 3",
        "sku": "F3-001",
        "precio": "5000",
        "precio_compra": "1000",
        "cantidad": "7",
        "stock_minimo": "2",
        "categoria_id": str(categoria.id),
    }
    datos.update(cambios)
    return client.post("/productos/nuevo", data=datos, follow_redirects=True)


def test_stock_inicial_genera_movimiento(admin_client):
    respuesta = _crear_producto_por_ruta(admin_client)
    assert "Producto registrado correctamente" in respuesta.get_data(as_text=True)

    producto = Producto.query.filter_by(sku="F3-001").first()
    assert producto.cantidad == 7
    assert producto.precio_compra == 1000

    movimiento = Movimiento.query.filter_by(producto_id=producto.id).one()
    assert movimiento.tipo == "entrada"
    assert movimiento.motivo == "inventario_inicial"
    assert movimiento.cantidad == 7
    assert movimiento.stock_anterior == 0
    assert movimiento.stock_nuevo == 7
    assert movimiento.costo_unitario == 1000
    assert movimiento.impacto == 7000


def test_editar_producto_no_cambia_cantidad_ni_costo(admin_client):
    _crear_producto_por_ruta(admin_client)
    producto = Producto.query.filter_by(sku="F3-001").first()

    respuesta = admin_client.post(
        f"/productos/{producto.id}/editar",
        data={
            "nombre": "Producto Fase 3 editado",
            "sku": "F3-001",
            "precio": "6000",
            "precio_compra": "9999",
            "cantidad": "999",
            "stock_minimo": "3",
        },
        follow_redirects=True,
    )
    assert "Producto actualizado" in respuesta.get_data(as_text=True)
    assert producto.cantidad == 7
    assert producto.precio_compra == 1000
    assert producto.precio == 6000


def test_desactivar_y_reactivar_producto(admin_client):
    _crear_producto_por_ruta(admin_client)
    producto = Producto.query.filter_by(sku="F3-001").first()

    respuesta = admin_client.post(f"/productos/{producto.id}/estado", follow_redirects=True)
    assert "desactivado" in respuesta.get_data(as_text=True)
    assert producto.activo is False

    listado = admin_client.get("/productos/").get_data(as_text=True)
    assert "Producto Fase 3" not in listado

    inactivos = admin_client.get("/productos/?estado=inactivos").get_data(as_text=True)
    assert "Producto Fase 3" in inactivos

    respuesta = admin_client.post(f"/productos/{producto.id}/estado", follow_redirects=True)
    assert "activado" in respuesta.get_data(as_text=True)
    assert producto.activo is True


def test_entrada_por_ruta_actualiza_costo(admin_client):
    _crear_producto_por_ruta(admin_client)
    producto = Producto.query.filter_by(sku="F3-001").first()

    respuesta = admin_client.post(
        "/movimientos/registrar",
        data={
            "producto_id": str(producto.id),
            "tipo": "entrada",
            "cantidad": "3",
            "costo_unitario": "2000",
            "actualizar_costo": "on",
            "observacion": "Compra de prueba",
        },
        follow_redirects=True,
    )
    assert "Entrada registrada" in respuesta.get_data(as_text=True)
    assert producto.cantidad == 10
    assert producto.precio_compra == 1300

    movimiento = Movimiento.query.order_by(Movimiento.id.desc()).first()
    assert movimiento.tipo == "entrada"
    assert movimiento.stock_anterior == 7
    assert movimiento.stock_nuevo == 10
    assert movimiento.impacto == 6000


def test_salida_insuficiente_no_modifica_stock(admin_client):
    _crear_producto_por_ruta(admin_client)
    producto = Producto.query.filter_by(sku="F3-001").first()

    respuesta = admin_client.post(
        "/movimientos/registrar",
        data={"producto_id": str(producto.id), "tipo": "salida", "cantidad": "100"},
        follow_redirects=True,
    )
    assert "Stock insuficiente" in respuesta.get_data(as_text=True)
    assert producto.cantidad == 7
