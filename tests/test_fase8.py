import re
from datetime import datetime

from app import db
from app.models import Movimiento, Producto, Sucursal, Usuario
from app.services.inventario import registrar_salida
from app.services.rotacion import obtener_rotacion


def _sucursal(app, nombre="Sucursal Norte"):
    with app.app_context():
        existente = Sucursal.query.filter_by(nombre=nombre).first()
        if existente:
            return existente.id
        sucursal = Sucursal(nombre=nombre)
        db.session.add(sucursal)
        db.session.commit()
        return sucursal.id


def _producto(app, nombre, sku, sucursal_id=1, cantidad=10):
    with app.app_context():
        producto = Producto(
            nombre=nombre,
            sku=sku,
            precio=1000,
            precio_compra=600,
            cantidad=cantidad,
            stock_minimo=1,
            activo=True,
            sucursal_id=sucursal_id,
        )
        db.session.add(producto)
        db.session.commit()
        return producto.id


def _kpi(html, etiqueta):
    patron = r'<div class="kpi-value">([^<]*)</div><div class="kpi-label">' + re.escape(etiqueta)
    encontrado = re.search(patron, html)
    return encontrado.group(1).strip() if encontrado else None


def test_tendero_ve_selector_de_sucursal(admin_client):
    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert 'name="sucursal_id"' in html
    assert "Sucursal activa" in html
    assert "Principal" in html


def test_cambio_de_sucursal_aisla_productos(app, admin_client):
    norte = _sucursal(app)
    _producto(app, "Solo Principal", "SUC-001", 1)
    _producto(app, "Solo Norte", "SUC-002", norte)

    html = admin_client.get("/productos/").get_data(as_text=True)
    assert "Solo Principal" in html
    assert "Solo Norte" not in html

    respuesta = admin_client.post(
        "/sucursales/cambiar", data={"sucursal_id": norte}, follow_redirects=True
    )
    assert "Ahora opera en la sucursal «Sucursal Norte»" in respuesta.get_data(as_text=True)

    html = admin_client.get("/productos/").get_data(as_text=True)
    assert "Solo Norte" in html
    assert "Solo Principal" not in html

    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Resumen general del inventario · Sucursal Norte" in html


def test_cambio_de_sucursal_invalido_no_altera_la_activa(admin_client):
    respuesta = admin_client.post(
        "/sucursales/cambiar", data={"sucursal_id": 9999}, follow_redirects=True
    )
    html = respuesta.get_data(as_text=True)
    assert "La sucursal seleccionada no está disponible" in html
    assert "Resumen general del inventario · Principal" in html


def test_cajero_no_puede_cambiar_de_sucursal(cajero_client):
    respuesta = cajero_client.post(
        "/sucursales/cambiar", data={"sucursal_id": 2}, follow_redirects=True
    )
    assert "Acción permitida solo para administradores" in respuesta.get_data(as_text=True)


def test_dashboard_suma_solo_la_sucursal_activa(app, admin_client):
    norte = _sucursal(app)
    _producto(app, "Producto A", "DASH8-001", 1, cantidad=4)
    _producto(app, "Producto B", "DASH8-002", 1, cantidad=6)
    _producto(app, "Producto C", "DASH8-003", norte, cantidad=100)

    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert _kpi(html, "Total de productos") == "2"
    assert _kpi(html, "Unidades en stock") == "10"


def test_historial_filtra_por_sucursal(app, admin_client):
    norte = _sucursal(app)
    principal_id = _producto(app, "Mov Principal", "MOV8-001", 1)
    norte_id = _producto(app, "Mov Norte", "MOV8-002", norte)

    with app.app_context():
        producto = db.session.get(Producto, principal_id)
        admin = Usuario.query.filter_by(username="admin").first()
        registrar_salida(producto, 2, usuario=admin)
        db.session.add(Movimiento(
            producto_id=norte_id, sucursal_id=norte, tipo="salida",
            motivo="venta", cantidad=1, delta=-1,
        ))
        db.session.commit()

    html = admin_client.get("/movimientos/").get_data(as_text=True)
    assert "Mov Principal" in html
    assert "Mov Norte" not in html


def test_csv_de_productos_filtra_por_sucursal(app, admin_client):
    norte = _sucursal(app)
    _producto(app, "Reporte Principal", "CSV8-001", 1)
    _producto(app, "Reporte Norte", "CSV8-002", norte)

    contenido = admin_client.get("/reportes/productos.csv").get_data(as_text=True)
    assert "Reporte Principal" in contenido
    assert "Reporte Norte" not in contenido


def test_venta_rechaza_producto_de_otra_sucursal(app, admin_client):
    norte = _sucursal(app)
    norte_id = _producto(app, "Ajeno a la sede", "VEN8-001", norte, cantidad=5)

    respuesta = admin_client.post(
        "/movimientos/venta",
        data={"producto_id": str(norte_id), "cantidad": "1"},
        follow_redirects=True,
    )
    assert "Seleccione un producto" in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Producto, norte_id).cantidad == 5


def test_producto_nuevo_usa_la_sucursal_activa(app, admin_client):
    norte = _sucursal(app)
    datos = {"precio": "1000", "cantidad": "5", "stock_minimo": "1", "precio_compra": "600"}

    admin_client.post("/productos/nuevo", data={"nombre": "Nuevo Principal", "sku": "NEW8-001", **datos},
                      follow_redirects=True)
    admin_client.post("/sucursales/cambiar", data={"sucursal_id": norte}, follow_redirects=True)
    admin_client.post("/productos/nuevo", data={"nombre": "Nuevo Norte", "sku": "NEW8-002", **datos},
                      follow_redirects=True)

    with app.app_context():
        principal = Producto.query.filter_by(sku="NEW8-001").first()
        otra = Producto.query.filter_by(sku="NEW8-002").first()
        assert principal.sucursal_id == 1
        assert otra.sucursal_id == norte
        movimiento = Movimiento.query.filter_by(producto_id=otra.id).one()
        assert movimiento.sucursal_id == norte


def test_rotacion_filtra_por_sucursal(app):
    norte = _sucursal(app)
    principal_id = _producto(app, "Rot Principal", "ROT8-001", 1)
    _producto(app, "Rot Norte", "ROT8-002", norte)

    with app.app_context():
        db.session.add(Movimiento(
            producto_id=principal_id, sucursal_id=1, tipo="salida",
            motivo="venta", cantidad=5, delta=-5, fecha=datetime.now(),
        ))
        db.session.commit()

        principal = obtener_rotacion(periodo=30, sucursal_id=1)
        otra = obtener_rotacion(periodo=30, sucursal_id=norte)

    assert [f["producto"].nombre for f in principal["filas"]] == ["Rot Principal"]
    assert principal["filas"][0]["unidades"] == 5
    assert [f["producto"].nombre for f in otra["filas"]] == ["Rot Norte"]
    assert otra["filas"][0]["unidades"] == 0


def test_cajero_solo_ve_y_opera_su_sucursal(app, cajero_client):
    norte = _sucursal(app)
    _producto(app, "Prod Principal", "CAJ8-001", 1)
    _producto(app, "Prod Norte", "CAJ8-002", norte)

    with app.app_context():
        cliente = Usuario.query.filter_by(username="cliente").first()
        cliente.sucursal_id = norte
        db.session.commit()
        principal_id = Producto.query.filter_by(sku="CAJ8-001").first().id
    # La sesión del contexto de pruebas conserva la identidad del usuario del login.
    db.session.expire_all()

    html = cajero_client.get("/productos/").get_data(as_text=True)
    assert "Prod Norte" in html
    assert "Prod Principal" not in html

    respuesta = cajero_client.post(
        "/movimientos/venta",
        data={"producto_id": str(principal_id), "cantidad": "1"},
        follow_redirects=True,
    )
    assert "Seleccione un producto" in respuesta.get_data(as_text=True)
