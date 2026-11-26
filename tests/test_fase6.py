from app import db
from app.models import Movimiento, Producto


def _crear_producto(app, nombre="Producto venta", sku="VTA-001", cantidad=10, precio=3000,
                    precio_compra=1500):
    with app.app_context():
        producto = Producto(
            nombre=nombre,
            sku=sku,
            precio=precio,
            precio_compra=precio_compra,
            cantidad=cantidad,
            stock_minimo=1,
            activo=True,
            sucursal_id=1,  # Principal
        )
        db.session.add(producto)
        db.session.commit()
        return producto.id


def test_dashboard_muestra_graficos_y_selector_de_periodo(admin_client):
    respuesta = admin_client.get("/dashboard")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert "chartVentas" in html
    assert "Ventas de los últimos 7 días" in html
    assert "Actividad de hoy" in html
    assert "Registrar venta" in html
    assert "7 días" in html
    assert "30 días" in html


def test_dashboard_respeta_periodo_y_valor_invalido(admin_client):
    html = admin_client.get("/dashboard?periodo=30").get_data(as_text=True)
    assert "Ventas de los últimos 30 días" in html

    html = admin_client.get("/dashboard?periodo=99").get_data(as_text=True)
    assert "Ventas de los últimos 7 días" in html


def test_dashboard_refleja_ventas_y_productos_mas_vendidos(app, admin_client):
    producto_id = _crear_producto(app, nombre="Café premium", sku="DASH-001", cantidad=20, precio=5000)
    admin_client.post(
        "/movimientos/venta",
        data={"producto_id": str(producto_id), "cantidad": "3"},
        follow_redirects=True,
    )

    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Café premium" in html
    assert "chartTop" in html
    assert "chartCategorias" in html
    assert "Detalle de los productos más vendidos" in html
    assert "15,000.00" in html


def test_cajero_registra_venta(app, cajero_client):
    producto_id = _crear_producto(app, nombre="Galleta", sku="VTA-100", cantidad=10, precio=2500)

    respuesta = cajero_client.post(
        "/movimientos/venta",
        data={"producto_id": str(producto_id), "cantidad": "4", "observacion": "Venta mostrador"},
        follow_redirects=True,
    )
    assert "Venta registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        producto = db.session.get(Producto, producto_id)
        assert producto.cantidad == 6
        movimiento = (Movimiento.query.filter_by(producto_id=producto_id)
                      .order_by(Movimiento.id.desc()).first())
        assert movimiento.tipo == "salida"
        assert movimiento.motivo == "venta"
        assert movimiento.cantidad == 4
        assert movimiento.delta == -4
        assert movimiento.stock_anterior == 10
        assert movimiento.stock_nuevo == 6
        assert movimiento.usuario.username == "cliente"


def test_cajero_no_puede_vender_mas_que_el_stock(app, cajero_client):
    producto_id = _crear_producto(app, nombre="Jugo", sku="VTA-200", cantidad=3, precio=1800)

    respuesta = cajero_client.post(
        "/movimientos/venta",
        data={"producto_id": str(producto_id), "cantidad": "5"},
        follow_redirects=True,
    )
    assert "Stock insuficiente" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Producto, producto_id).cantidad == 3
        assert Movimiento.query.filter_by(producto_id=producto_id).count() == 0


def test_cajero_no_accede_a_entradas_ni_ajustes(cajero_client):
    html = cajero_client.get("/movimientos/registrar", follow_redirects=True).get_data(as_text=True)
    assert "Acción permitida solo para administradores" in html

    html = cajero_client.get("/movimientos/ajuste", follow_redirects=True).get_data(as_text=True)
    assert "Acción permitida solo para administradores" in html


def test_dashboard_del_cajero_no_muestra_datos_de_lotes(cajero_client):
    respuesta = cajero_client.get("/dashboard")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert "chartVentas" in html
    assert "Estado de los lotes con stock" not in html
    assert "Mermas del mes" not in html
